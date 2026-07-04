"""
Bootstrap / enrich data/handlers.json from REAL detector output.

The routing map must reflect the exact strings the detectors emit, not guesses.
This tool derives entries from the labeled sample corpus under test/<format>/,
assigning each emitted string to the handler that owns that format directory.

Two modes:

  --live               Run every detector over test/<format>/* (needs the
                       Windows .exe toolchain). Authoritative source.
  --from-dump <file>   Parse an existing 'verify_detections.py' gap dump (works
                       anywhere, no exes). Add-only enrichment.

Both modes are merge-add: they never delete existing entries. Removals stay a
manual step, guided by the "unused keys" report from verify_detections.py.

A per-directory accept guard rejects cross-format misdetections (e.g. a PE/UPX
string emitted for an SFX .exe, or 'xar' misfired on an .arc), so auto-assigned
entries stay trustworthy. Generic/noise strings are dropped via
data/detection_blacklist.json.

Usage:
  python tools/build_handlers.py --live
  python tools/build_handlers.py --from-dump detections-dump
"""

import argparse
import json
import os
import re
import sys

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
DATA_PATH = os.path.join(SRC_PATH, 'data')
TEST_DIR = os.path.abspath(os.path.join(SRC_PATH, '..', 'test'))
HANDLERS_FILE = os.path.join(DATA_PATH, 'handlers.json')
BLACKLIST_FILE = os.path.join(DATA_PATH, 'detection_blacklist.json')

# test/<dir> -> (handler class name, accept keywords). A detection string is
# accepted for a directory only if it contains one of the keywords, which keeps
# cross-format misdetections out of the map.
DIR_HANDLERS = {
    '7z':       ('Format7zHandler',       ['7z', '7-zip', 'sevenzip']),
    'ace':      ('FormatAceHandler',      ['ace']),
    'alz':      ('FormatAlzipHandler',    ['alz', 'alzip']),
    'arc':      ('FormatArcHandler',      ['arc', 'freearc']),
    'bcm':      ('FormatBcmHandler',      ['bcm']),
    'gzip':     ('Format7zHandler',       ['gzip', 'gz']),
    'iss':      ('FormatInnoSetupHandler', ['inno']),
    'kgb':      ('FormatKgbHandler',      ['kgb']),
    'nsis':     ('Format7zHandler',       ['nsis', 'nullsoft']),
    'pea':      ('FormatPeaHandler',      ['pea', 'peazip']),
    'rar':      ('FormatRarHandler',      ['rar']),
    'squashfs': ('Format7zHandler',       ['squash', 'sqsh']),
    'uharc':    ('FormatUharcHandler',    ['uharc', 'uha']),
    'zpaq':     ('FormatZpaqHandler',     ['zpaq']),
}


def load_blacklist():
    with open(BLACKLIST_FILE, encoding='utf-8') as fh:
        data = json.load(fh)
    return (
        set(data.get('mime', [])),
        set(data.get('detection_exact', [])),
        list(data.get('detection_substrings', [])),
    )


def is_blacklisted_detection(value, exact, substrings):
    return value in exact or any(sub in value for sub in substrings)


def accepted_for_dir(value, keywords):
    return any(kw in value for kw in keywords)


def parse_dump(dump_path):
    """Parse a verify_detections gap dump into {dir: {'mime': set, 'detect': set}}."""
    result = {}
    current_dir = None
    header = re.compile(r'^\[(.+)\]\s*$')
    for raw in open(dump_path, encoding='utf-8', errors='replace'):
        line = raw.rstrip('\r\n')
        match = header.match(line.strip())
        if match:
            rel = match.group(1).replace('\\', '/')
            current_dir = rel.split('/')[0] if '/' in rel else None
            continue
        if current_dir is None:
            continue
        stripped = line.strip()
        if stripped.startswith('MIME gap'):
            result.setdefault(current_dir, {'mime': set(), 'detect': set()})['mime'].add(
                stripped.split(':', 1)[1].strip().lower())
        elif stripped.startswith('detect gap'):
            result.setdefault(current_dir, {'mime': set(), 'detect': set()})['detect'].add(
                stripped.split(':', 1)[1].strip().lower())
    return result


def collect_live():
    """Run every detector over the corpus. Returns {dir: {'mime': set, 'detect': set}}."""
    sys.path.insert(0, SRC_PATH)
    import logging
    logging.disable(logging.CRITICAL)
    from file_type import (
        determine_file_type_with_magic, determine_file_type_with_binwalk,
        determine_file_type_with_die, determine_file_type_with_trid,
        determine_file_type_with_magika,
    )
    bin_path = os.path.join(SRC_PATH, 'bin')

    result = {}
    for name in sorted(os.listdir(TEST_DIR)):
        format_dir = os.path.join(TEST_DIR, name)
        if not os.path.isdir(format_dir) or name not in DIR_HANDLERS:
            continue
        bucket = result.setdefault(name, {'mime': set(), 'detect': set()})
        for sample in os.listdir(format_dir):
            path = os.path.join(format_dir, sample)
            if not os.path.isfile(path):
                continue
            magic = determine_file_type_with_magic(file_path=path, fast_check=False)
            if magic:
                bucket['mime'].update(v.lower() for v in magic)
            magika = determine_file_type_with_magika(file_path=path, bin_path=bin_path)
            if magika:
                bucket['mime'].update(v.lower() for v in magika['mime_types'])
                bucket['detect'].update(v.lower() for v in magika['labels'])
            for detector in (determine_file_type_with_binwalk, determine_file_type_with_die,
                             determine_file_type_with_trid):
                found = detector(file_path=path, bin_path=bin_path)
                if found:
                    bucket['detect'].update(v.lower() for v in found)
    return result


def main():
    parser = argparse.ArgumentParser(description="Build/enrich data/handlers.json from real detector output.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--live', action='store_true', help="Run detectors over the corpus (needs Windows exes).")
    group.add_argument('--from-dump', metavar='FILE', help="Parse an existing verify_detections gap dump.")
    args = parser.parse_args()

    mime_black, det_exact, det_subs = load_blacklist()
    emitted = collect_live() if args.live else parse_dump(args.from_dump)

    with open(HANDLERS_FILE, encoding='utf-8') as fh:
        handlers = json.load(fh)
    mime_map = handlers.setdefault('mime_handlers', {})
    det_map = handlers.setdefault('detection_handlers', {})

    added_mime, added_det, rejected = [], [], []
    for format_dir, buckets in sorted(emitted.items()):
        if format_dir not in DIR_HANDLERS:
            continue
        handler, keywords = DIR_HANDLERS[format_dir]

        for value in sorted(buckets['mime']):
            if value in mime_black or value in mime_map:
                continue
            # only accept format-specific MIME (has a subtype hint from the format)
            if accepted_for_dir(value, keywords):
                mime_map[value] = handler
                added_mime.append((value, handler))
            else:
                rejected.append((format_dir, 'mime', value))

        for value in sorted(buckets['detect']):
            if is_blacklisted_detection(value, det_exact, det_subs) or value in det_map:
                continue
            if accepted_for_dir(value, keywords):
                det_map[value] = handler
                added_det.append((value, handler))
            else:
                rejected.append((format_dir, 'detect', value))

    with open(HANDLERS_FILE, 'w', encoding='utf-8') as fh:
        json.dump(handlers, fh, indent=2, ensure_ascii=False)
        fh.write('\n')

    print(f"Added {len(added_mime)} MIME + {len(added_det)} detection entries to {os.path.relpath(HANDLERS_FILE)}")
    for value, handler in added_mime:
        print(f"  + MIME    {value} -> {handler}")
    for value, handler in added_det:
        print(f"  + detect  {value} -> {handler}")
    if rejected:
        print(f"\nRejected {len(rejected)} strings (blacklist or accept-guard); review if a real format was dropped:")
        for format_dir, kind, value in rejected:
            print(f"  - [{format_dir}] {kind}: {value}")


if __name__ == '__main__':
    main()
