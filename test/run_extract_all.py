"""
End-to-end extraction smoke test.

Runs `main.py extract` over every sample under test/<format>/ and reports which
formats actually extract (produce output files). Must run on Windows, where the
bundled extractor .exe binaries work.

Usage:  python test/run_extract_all.py
"""

import os
import sys
import subprocess
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PY = os.path.join(TEST_DIR, '..', 'src', 'main.py')

# Non-sample files living under test/.
SKIP_EXTENSIONS = {'.py', '.md', '.txt', '.readme', '.about', '.ini', '.test'}
SKIP_DIRS = {'__pycache__', 'defs'}


def iter_samples():
    """Yield (format_dir, sample_path) for every candidate sample under test/."""
    for name in sorted(os.listdir(TEST_DIR)):
        format_dir = os.path.join(TEST_DIR, name)
        if not os.path.isdir(format_dir) or name in SKIP_DIRS:
            continue
        for root, dirs, files in os.walk(format_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for sample in files:
                if os.path.splitext(sample)[1].lower() in SKIP_EXTENSIONS:
                    continue
                yield name, os.path.join(root, sample)


def extracted_something(output_dir):
    """True if the output directory ended up with any file."""
    for _root, _dirs, files in os.walk(output_dir):
        if files:
            return True
    return False


def main():
    results = []
    for fmt, sample in iter_samples():
        output_dir = tempfile.mkdtemp(prefix='mx_')
        proc = subprocess.run(
            [sys.executable, MAIN_PY, 'extract', sample, output_dir],
            capture_output=True, text=True,
        )
        ok = proc.returncode == 0 and extracted_something(output_dir)
        results.append((fmt, os.path.relpath(sample, TEST_DIR), ok))
        status = 'OK  ' if ok else 'FAIL'
        print(f"[{status}] {fmt:14} {os.path.relpath(sample, TEST_DIR)}")

    passed = sum(1 for _f, _s, ok in results if ok)
    print(f"\n{passed}/{len(results)} samples extracted successfully")
    failed = [f"{f}:{s}" for f, s, ok in results if not ok]
    if failed:
        print("Failed:", ", ".join(failed))


if __name__ == '__main__':
    main()
