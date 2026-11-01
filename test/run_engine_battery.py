"""
Engine battery: the extractor contract, checked engine by engine.

run_battery.py proves every sample format extracts through the whole CLI
(detection, candidate chain, atomic staging). This battery instead calls each
engine (handler class) directly on its own samples, with no detection, no
fallback chain and no staging around it, so a misbehaving engine cannot hide
behind another handler or behind the CLI's safety nets. Run it whenever an
extractor is added or updated.

Checks, each on a copy of the sample in a throwaway folder:
  FRESH       extract() into a new, empty folder -> True, files inside it,
              nothing written beside that folder or beside the source.
  EXISTING    extract() into a folder that already has a file -> True, new
              files inside, the existing file untouched, nothing beside it.
  FOREIGN     extract() on a plain text file -> False, nothing extracted.
              A tool that exits 0 on a file it cannot open must be caught
              with run_extraction(failure_markers=...).
  FOREIGN-PE  engines of the PE fallback chain only (they are tried on every
              unrecognised .exe): extract() on a PE that is not theirs -> False.

Every registered engine must be listed in ENGINE_SAMPLES; an engine with no
sample is reported as NO SAMPLE.

WINDOWS ONLY: the engines are the bundled .exe tools under cli/bin/extractors.

Usage:
    python test/run_engine_battery.py                      # every engine
    python test/run_engine_battery.py FormatAceHandler ... # only these engines
    python test/run_engine_battery.py --timeout 300        # per tool run (s)
"""

import argparse
import io
import logging
import os
import shutil
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TEST_DIR)
SAMPLES_DIR = os.path.join(TEST_DIR, 'samples')
sys.path.insert(0, os.path.join(REPO_ROOT, 'src', 'cli'))

from cli_paths import BIN_PATH  # noqa: E402
from detection import PE_INSTALLER_FALLBACK  # noqa: E402
from formats import HANDLER_REGISTRY  # noqa: E402

# Samples (relative to test/samples) each engine must extract. Add the
# samples of a new engine here when you install it.
ENGINE_SAMPLES = {
    'Format7zHandler': ['7z/test-file.7z', 'zip/test.zip'],
    'Format7zExtHandler': ['asar/test-file.asar', 'lz4/test-file.lz4', 'pyinstaller/test-file.exe'],
    'Format7zZsHandler': ['squashfs/test-file-lz4.sqsh', 'lzip/some.lz'],
    'FormatRarHandler': ['rar/test-file.rar', 'rar/test-file.exe'],
    'FormatAceHandler': ['ace/test-file.ace', 'ace/test-file.exe'],
    'FormatKgbHandler': ['kgb/test-file.kgb', 'kgb/test-file.exe'],
    'FormatUharcHandler': ['uharc/test-file.uha', 'uharc/test-file.exe'],
    'FormatZpaqHandler': ['zpaq/test-file.zpaq'],
    'FormatAlzipHandler': ['alz/test-file.alz'],
    'FormatEggHandler': ['egg/test-file.egg'],
    'FormatBcmHandler': ['bcm/test-file-v1.bcm', 'bcm/test-file-v2.bcm'],
    'FormatArcHandler': ['arc/test-file.arc', 'arc/test-file.exe'],
    'FormatPeaHandler': ['pea/test-file.pea'],
    'FormatInnoSetupHandler': ['iss/test-file.exe'],
    'FormatMsiHandler': ['msi/7z920.msi'],
    'FormatBitrockHandler': [],
    'FormatCicdecHandler': ['cic/test-file.exe'],
    'FormatDgcaHandler': ['dgca/test-file.dgc'],
    'FormatWixHandler': ['msi/7z920.msi'],
    'FormatInstallShieldHandler': [],
    'FormatLzipHandler': ['lzip/some.lz', 'lzip/sample.tar.lz'],
}

FOREIGN_TEXT = os.path.join(SAMPLES_DIR, 'test-file.txt')
# Any PE that is neither an archive nor an installer.
FOREIGN_PE = os.path.join(REPO_ROOT, 'src', 'cli', 'bin', 'extractors', 'plzip', 'plzip.exe')
KEEP_NAME, KEEP_TEXT = 'keep-me.txt', 'existing content\n'


def bound_tool_runs(timeout):
    """Every tool run gets no console input and a time limit, so a tool that
    waits for a key press fails the check instead of hanging the battery."""
    real_run = subprocess.run

    def bounded_run(*args, **kwargs):
        kwargs.setdefault('stdin', subprocess.DEVNULL)
        kwargs.setdefault('timeout', timeout)
        return real_run(*args, **kwargs)

    subprocess.run = bounded_run


def run_engine(engine, source, seed_existing=False):
    """
    Copy `source` into a throwaway folder and call engine.extract() into
    <work>/out. Returns (result, problems, captured log, extracted names).
    """
    work = tempfile.mkdtemp(prefix='mx_engine_')
    src_dir, out_dir = os.path.join(work, 'src'), os.path.join(work, 'out')
    os.makedirs(src_dir)
    os.makedirs(out_dir)
    target = os.path.join(src_dir, os.path.basename(source))
    shutil.copy2(source, target)
    if seed_existing:
        with open(os.path.join(out_dir, KEEP_NAME), 'w', encoding='utf-8') as fh:
            fh.write(KEEP_TEXT)

    log_stream = io.StringIO()
    log_handler = logging.StreamHandler(log_stream)
    log_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)
    problems = []
    try:
        args = argparse.Namespace(file_path=target, output_dir=out_dir, password=None)
        handler = HANDLER_REGISTRY[engine](cli_args=args, bin_path=BIN_PATH)
        handler.extract_directory = out_dir
        try:
            result = handler.extract()
        except Exception as exc:  # an engine must never raise
            problems.append(f"extract() raised {type(exc).__name__}: {exc}")
            result = None

        beside = sorted(set(os.listdir(work)) - {'src', 'out'})
        if beside:
            problems.append(f"wrote beside the output folder: {beside}")
        next_to_source = sorted(set(os.listdir(src_dir)) - {os.path.basename(target)})
        if next_to_source:
            problems.append(f"wrote next to the source: {next_to_source}")
        if seed_existing:
            keep = os.path.join(out_dir, KEEP_NAME)
            if not os.path.isfile(keep):
                problems.append("the existing file in the output folder was removed")
            else:
                with open(keep, encoding='utf-8') as fh:
                    if fh.read() != KEEP_TEXT:
                        problems.append("the existing file in the output folder was changed")
        extracted = sorted(set(os.listdir(out_dir)) - {KEEP_NAME})
        return result, problems, log_stream.getvalue(), extracted
    finally:
        root_logger.removeHandler(log_handler)
        shutil.rmtree(work, ignore_errors=True)


def check_extracts(engine, source, seed_existing):
    result, problems, log, extracted = run_engine(engine, source, seed_existing)
    if result is not True:
        problems.append(f"extract() returned {result!r}, expected True")
    if not extracted:
        problems.append("nothing was extracted")
    return problems, log


def check_rejects(engine, source):
    result, problems, log, extracted = run_engine(engine, source)
    if result is not False:
        problems.append(f"extract() returned {result!r} on a file that is not its format, expected False")
    if extracted:
        problems.append(f"extracted {extracted} from a file that is not its format")
    return problems, log


def main():
    parser = argparse.ArgumentParser(description="Extractor contract, engine by engine.")
    parser.add_argument('engines', nargs='*', help="Engine (handler class) names; default: all.")
    parser.add_argument('--timeout', type=int, default=180, help="Per tool run, in seconds.")
    opts = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)  # each check captures its own log
    bound_tool_runs(opts.timeout)

    unknown = [name for name in opts.engines if name not in HANDLER_REGISTRY]
    if unknown:
        print(f"Unknown engine(s): {', '.join(unknown)}")
        return 2
    engines = opts.engines or list(HANDLER_REGISTRY)
    if os.name != 'nt':
        print("WARNING: the engines are Windows .exe tools; every check fails off Windows.")

    unlisted = [name for name in engines if name not in ENGINE_SAMPLES]
    rows, failures, missing = [], 0, []
    for engine in engines:
        samples = ENGINE_SAMPLES.get(engine, [])
        if not samples:
            missing.append(engine)
            continue
        checks = []
        for rel in samples:
            source = os.path.join(SAMPLES_DIR, rel)
            checks.append((rel, 'FRESH', *check_extracts(engine, source, seed_existing=False)))
            checks.append((rel, 'EXISTING', *check_extracts(engine, source, seed_existing=True)))
        checks.append(('(text file)', 'FOREIGN', *check_rejects(engine, FOREIGN_TEXT)))
        if engine in PE_INSTALLER_FALLBACK:
            checks.append(('(plain PE)', 'FOREIGN-PE', *check_rejects(engine, FOREIGN_PE)))
        rows.append((engine, checks))

    print("=" * 78)
    print("ENGINE BATTERY: extractor contract, engine by engine (WINDOWS ONLY)")
    print("=" * 78)
    for engine, checks in rows:
        engine_ok = all(not problems for _rel, _check, problems, _log in checks)
        print(f"{'PASS' if engine_ok else 'FAIL':<5} {engine}")
        for rel, check, problems, log in checks:
            print(f"        {'ok' if not problems else 'FAIL':<5} {check:<11} {rel}")
            if problems:
                failures += 1
                for problem in problems:
                    print(f"              ! {problem}")
                for line in log.strip().splitlines()[-8:]:
                    print(f"              | {line}")
    for engine in missing:
        print(f"{'-':<5} {engine}: NO SAMPLE (add one to test/samples and ENGINE_SAMPLES)")
    for engine in unlisted:
        print(f"{'-':<5} {engine}: not listed in ENGINE_SAMPLES")

    total = sum(len(checks) for _engine, checks in rows)
    print()
    print(f"  {total - failures}/{total} checks passed over {len(rows)} engine(s)"
          + (f"; {len(missing)} without sample" if missing else ""))
    return 0 if failures == 0 and total > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
