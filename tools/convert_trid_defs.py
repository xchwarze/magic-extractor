"""
Convert the public TrID XML definitions into data/signatures.json.

TrID (https://mark0.net) ships per-format XML defs with the file-type name, MIME
and front-block byte patterns. This harvests the defs whose file-type name (or
MIME) is already a routing key in data/handlers.json and writes them as native
magic signatures, so `determine_file_type_with_signatures` can name those formats
without running trid.exe.

Usage:
  python tools/convert_trid_defs.py [<trid_defs_dir>]     (default: triddefs_xml/defs)
"""

import json
import os
import sys
import xml.etree.ElementTree as ET

# Hand-authored signatures for format variants the TrID defs miss.
SUPPLEMENTS = [
    # TrID only knows BCM v1 ("BCM!"); add BCM v2 ("BCM2").
    {'name': 'bcm compressed archive', 'patterns': [{'pos': 0, 'hex': '42434d32'}]},
]

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DATA_PATH = os.path.join(ROOT, 'src', 'data')
HANDLERS_FILE = os.path.join(DATA_PATH, 'handlers.json')
SIGNATURES_FILE = os.path.join(DATA_PATH, 'signatures.json')
DEFAULT_DEFS_DIR = os.path.join(ROOT, 'triddefs_xml', 'defs')


def parse_def(path):
    """Return (name, mime, [{'pos':int,'hex':str}, ...]) for a TrID def, or None."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None

    info = root.find('Info')
    if info is None:
        return None
    name = (info.findtext('FileType') or '').strip()
    mime = (info.findtext('Mime') or '').strip()

    patterns = []
    front = root.find('FrontBlock')
    if front is not None:
        for pattern in front.findall('Pattern'):
            hex_bytes = (pattern.findtext('Bytes') or '').strip()
            pos = (pattern.findtext('Pos') or '0').strip()
            if hex_bytes:
                patterns.append({'pos': int(pos), 'hex': hex_bytes})

    if not name or not patterns:
        return None
    return name, mime, patterns


def main():
    defs_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DEFS_DIR
    if not os.path.isdir(defs_dir):
        print(f"TrID defs dir not found: {defs_dir}")
        sys.exit(1)

    with open(HANDLERS_FILE, encoding='utf-8') as fh:
        handlers = json.load(fh)
    detection_handlers = handlers.setdefault('detection_handlers', {})
    mime_handlers = handlers.get('mime_handlers', {})
    # lowercased lookup for resolving a def to its handler
    detection_lc = {k.lower(): v for k, v in detection_handlers.items()}
    mime_lc = {k.lower(): v for k, v in mime_handlers.items()}

    signatures, scanned, added_keys = [], 0, 0
    for current_root, _dirs, files in os.walk(defs_dir):
        for name in files:
            if not name.lower().endswith('.trid.xml'):
                continue
            scanned += 1
            parsed = parse_def(os.path.join(current_root, name))
            if not parsed:
                continue
            file_type, mime, patterns = parsed

            # resolve the handler this def routes to (by name, else by MIME)
            key = file_type.lower()
            handler = detection_lc.get(key) or mime_lc.get(mime.lower())
            if not handler:
                continue

            # ensure the detection name routes, then record the signature
            if key not in detection_lc:
                detection_handlers[file_type.lower()] = handler
                detection_lc[key] = handler
                added_keys += 1
            signatures.append({'name': key, 'patterns': patterns})

    # add hand-authored supplements (their names must already route via a def)
    for supplement in SUPPLEMENTS:
        if supplement['name'] in detection_lc:
            signatures.append(supplement)

    # dedupe by (name, patterns)
    seen, unique = set(), []
    for sig in signatures:
        dedupe_key = (sig['name'], tuple((p['pos'], p['hex']) for p in sig['patterns']))
        if dedupe_key not in seen:
            seen.add(dedupe_key)
            unique.append(sig)

    with open(SIGNATURES_FILE, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(unique, fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    with open(HANDLERS_FILE, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(handlers, fh, indent=2, ensure_ascii=False)
        fh.write('\n')

    print(f"Scanned {scanned} defs; wrote {len(unique)} signatures to {os.path.relpath(SIGNATURES_FILE, ROOT)}")
    print(f"Added {added_keys} new detection keys to {os.path.relpath(HANDLERS_FILE, ROOT)}")


if __name__ == '__main__':
    main()
