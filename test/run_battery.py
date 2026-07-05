"""
Full test battery for magic-extractor.

Two independent stages, run back-to-back:

  1. Pure-python unit tests  (runs ANYWHERE, incl. WSL/Linux/macOS)
     Discovers and runs test/gui/test_*.py and test/test_delete_source.py
     in-process with the stdlib `unittest` runner. These exercise pure logic
     (GUI command building, config/history/paths, delete_source) and never
     touch the bundled binaries.

  2. Extraction battery      (WINDOWS ONLY)
     Walks every sample file under test/<format>/ and runs both
     `python cli/main.py identify <file>` and
     `python cli/main.py extract  <file> <tmp_out>` on each, recording the
     exit code and whether a handler actually produced output.

     >>> The extraction battery only works on the user's Windows host. <<<
     The detectors (die/binwalk/magika) and extractors (7z/unrar/unace/...)
     shipped under cli/bin/ are Windows PE `.exe` files. This repo lives on a
     Windows drive mounted in WSL, and WSL has no binfmt handler registered for
     Windows executables, so those tools cannot run under WSL. Stage 2 will
     therefore report every sample as FAIL if run under WSL/Linux -- that is
     expected; run it from a Windows `python` (cmd/PowerShell), not from WSL.
     Stage 1 has no such restriction and passes everywhere.

This script builds ON the existing helpers rather than duplicating them:
it reuses the sample-walking + "did it extract" logic pioneered in
run_extract_all.py, and the stdlib-unittest layout of the test_*.py suites.

Usage:
    python test/run_battery.py                 # both stages
    python test/run_battery.py --unit-only     # stage 1 only (safe in WSL)
    python test/run_battery.py --battery-only  # stage 2 only (Windows)
    python test/run_battery.py --timeout 300   # per-command timeout (seconds)

Exit code is 0 only when every executed item passed; non-zero if any unit
test or any battery item (identify or extract) failed.
"""

import argparse
import io
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TEST_DIR)
MAIN_PY = os.path.join(REPO_ROOT, 'cli', 'main.py')
GUI_TEST_DIR = os.path.join(TEST_DIR, 'gui')

# Non-sample files living under test/: this runner's own helper scripts, docs,
# and installer *source* scripts (.nsi/.iss) that are inputs to a build, not
# extraction targets. The real samples in nsis/ and iss/ are the .exe files.
SKIP_EXTENSIONS = {
    '.py', '.pyc', '.md', '.txt', '.readme', '.about',
    '.ini', '.test', '.nsi', '.iss',
}
# Directories under test/ that are not sample corpora.
SKIP_DIRS = {'__pycache__', 'defs', 'gui'}


# --------------------------------------------------------------------------- #
# Stage 1: pure-python unit tests
# --------------------------------------------------------------------------- #
def build_unit_suite():
    """Collect the stdlib-unittest suites that run without the .exe toolchain."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # test/gui/test_*.py -- top_level_dir is the gui dir so the modules load as
    # bare `test_*` names (each file injects the repo root itself to import the
    # real `gui` package); using test/ as top level would shadow that package.
    if os.path.isdir(GUI_TEST_DIR):
        suite.addTests(loader.discover(
            start_dir=GUI_TEST_DIR, pattern='test_*.py', top_level_dir=GUI_TEST_DIR))

    # test/test_delete_source.py (imports cli/helpers.py, which it puts on path).
    suite.addTests(loader.discover(
        start_dir=TEST_DIR, pattern='test_delete_source.py', top_level_dir=TEST_DIR))

    return suite


def run_unit_tests():
    """Run stage 1 in-process; return (ok, total, failures, errors, skipped)."""
    print("=" * 72)
    print("STAGE 1: pure-python unit tests (runs anywhere)")
    print("=" * 72)

    suite = build_unit_suite()
    stream = io.StringIO()
    # The delete_source tests deliberately log ERROR/WARNING on their sad paths;
    # silence logging so the report stays clean (restored afterwards).
    logging.disable(logging.CRITICAL)
    try:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    finally:
        logging.disable(logging.NOTSET)

    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total - failures - errors - skipped
    ok = failures == 0 and errors == 0

    print(f"  ran {total}  |  pass {passed}  fail {failures}  "
          f"error {errors}  skip {skipped}")
    if not ok:
        # Only dump the verbose runner output when something is wrong.
        print("-" * 72)
        print(stream.getvalue().rstrip())
        print("-" * 72)
    print(f"STAGE 1: {'PASS' if ok else 'FAIL'}\n")
    return ok, total, failures, errors, skipped


# --------------------------------------------------------------------------- #
# Stage 2: extraction battery (Windows only)
# --------------------------------------------------------------------------- #
def iter_samples():
    """Yield (format_dir_name, sample_path) for every sample under test/<fmt>/."""
    for name in sorted(os.listdir(TEST_DIR)):
        format_dir = os.path.join(TEST_DIR, name)
        if not os.path.isdir(format_dir) or name in SKIP_DIRS:
            continue
        for root, dirs, files in os.walk(format_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for sample in sorted(files):
                if os.path.splitext(sample)[1].lower() in SKIP_EXTENSIONS:
                    continue
                yield name, os.path.join(root, sample)


def extracted_something(output_dir):
    """True if the output directory ended up with any file (any depth)."""
    for _root, _dirs, files in os.walk(output_dir):
        if files:
            return True
    return False


def first_candidate(identify_stdout):
    """Pull the first 'Candidate handlers' entry from `identify` output, if any."""
    lines = identify_stdout.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Candidate handlers"):
            for follow in lines[index + 1:]:
                stripped = follow.strip()
                if stripped.startswith("- "):
                    return stripped[2:]
            break
    return ""


def run_cli(command, sample, extra=None, timeout=180):
    """Run `python cli/main.py <command> <sample> [extra]`; return (rc, stdout)."""
    argv = [sys.executable, MAIN_PY, command, sample]
    if extra:
        argv.append(extra)
    try:
        proc = subprocess.run(
            argv,
            capture_output=True, text=True,
            stdin=subprocess.DEVNULL,  # never block on an interactive prompt
            timeout=timeout,
        )
        return proc.returncode, proc.stdout or ""
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError as exc:  # e.g. python/main.py missing
        return 127, str(exc)


def run_one_sample(fmt, sample, timeout):
    """identify + extract one sample into a throwaway dir; return a result dict."""
    id_rc, id_out = run_cli('identify', sample, timeout=timeout)
    id_ok = id_rc == 0
    handler = first_candidate(id_out)

    out_dir = tempfile.mkdtemp(prefix='mx_battery_')
    try:
        ex_rc, _ = run_cli('extract', sample, extra=out_dir, timeout=timeout)
        ex_ok = ex_rc == 0 and extracted_something(out_dir)
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)  # never touch the corpus

    return {
        'fmt': fmt,
        'sample': os.path.relpath(sample, TEST_DIR),
        'handler': handler,
        'id_ok': id_ok,
        'id_rc': id_rc,
        'ex_ok': ex_ok,
        'ex_rc': ex_rc,
        'ok': id_ok and ex_ok,
    }


def run_extraction_battery(timeout):
    """Run stage 2 over every sample; print a per-sample table; return (ok, results)."""
    print("=" * 72)
    print("STAGE 2: extraction battery  (WINDOWS ONLY -- needs cli/bin/*.exe)")
    if os.name != 'nt':
        print("  WARNING: os.name != 'nt' -- the bundled .exe detectors/extractors")
        print("           cannot run here (WSL/Linux has no binfmt for Windows PE).")
        print("           Every sample below is expected to FAIL; run on Windows.")
    print("=" * 72)

    if not os.path.isfile(MAIN_PY):
        print(f"  ERROR: cannot find CLI entry at {MAIN_PY}")
        print("STAGE 2: FAIL\n")
        return False, []

    header = f"  {'STATUS':<6} {'FORMAT':<12} {'IDENT':<6} {'EXTRACT':<8} {'HANDLER':<26} SAMPLE"
    print(header)
    print("  " + "-" * (len(header) - 2))

    results = []
    for fmt, sample in iter_samples():
        try:
            res = run_one_sample(fmt, sample, timeout)
        except Exception as exc:  # keep the battery going on any unexpected error
            res = {'fmt': fmt, 'sample': os.path.relpath(sample, TEST_DIR),
                   'handler': '', 'id_ok': False, 'id_rc': -1,
                   'ex_ok': False, 'ex_rc': -1, 'ok': False, 'error': str(exc)}
        results.append(res)
        status = 'PASS' if res['ok'] else 'FAIL'
        print(f"  {status:<6} {res['fmt']:<12} "
              f"{'OK' if res['id_ok'] else 'FAIL':<6} "
              f"{'OK' if res['ex_ok'] else 'FAIL':<8} "
              f"{res['handler']:<26.26} {res['sample']}")

    passed = sum(1 for r in results if r['ok'])
    total = len(results)
    ok = passed == total and total > 0
    print()
    print(f"  {passed}/{total} samples passed (identify + extract)")
    failures = [f"{r['fmt']}:{r['sample']}" for r in results if not r['ok']]
    if failures:
        print("  Failed: " + ", ".join(failures))
    print(f"STAGE 2: {'PASS' if ok else 'FAIL'}\n")
    return ok, results


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="magic-extractor full test battery.")
    parser.add_argument('--unit-only', action='store_true',
                        help="Run only the pure-python unit tests (safe under WSL).")
    parser.add_argument('--battery-only', action='store_true',
                        help="Run only the extraction battery (Windows only).")
    parser.add_argument('--timeout', type=int, default=180,
                        help="Per-command timeout in seconds (default 180).")
    args = parser.parse_args()

    run_unit = not args.battery_only
    run_battery = not args.unit_only

    unit_ok = True
    battery_ok = True

    if run_unit:
        unit_ok = run_unit_tests()[0]
    if run_battery:
        battery_ok = run_extraction_battery(args.timeout)[0]

    print("=" * 72)
    print("SUMMARY")
    if run_unit:
        print(f"  unit tests      : {'PASS' if unit_ok else 'FAIL'}")
    if run_battery:
        print(f"  extraction battery: {'PASS' if battery_ok else 'FAIL'}")
    overall = unit_ok and battery_ok
    print(f"  overall         : {'PASS' if overall else 'FAIL'}")
    print("=" * 72)

    sys.exit(0 if overall else 1)


if __name__ == '__main__':
    main()
