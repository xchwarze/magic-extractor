"""
Generate data/handlers.json and data/signatures.json from the handler
declarations (detection_mimes / detection_names / detection_signatures).

Each handler owns its indicators; this collects them into the runtime data files.
An optional data/extra_detections.json is merged on top for extra detections not
tied to a single handler (it never overrides a handler-declared entry).

Usage:  python tools/generate_data.py
"""

import json
import os
import sys

SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
DATA_PATH = os.path.join(SRC_PATH, 'data')
sys.path.insert(0, SRC_PATH)

import formats

HANDLERS_FILE = os.path.join(DATA_PATH, 'handlers.json')
SIGNATURES_FILE = os.path.join(DATA_PATH, 'signatures.json')
EXTRAS_FILE = os.path.join(DATA_PATH, 'extra_detections.json')


def _write_json(path, data):
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write('\n')


def main():
    mime_handlers, detection_handlers, signatures = {}, {}, []

    for handler_name, handler in sorted(formats.HANDLER_REGISTRY.items()):
        for mime in handler.detection_mimes():
            mime_handlers[mime.lower()] = handler_name
        for name in handler.detection_names():
            detection_handlers[name.lower()] = handler_name
        for signature in handler.detection_signatures():
            key = signature['name'].lower()
            detection_handlers[key] = handler_name       # ensure the magic name routes
            signatures.append({'name': key, 'patterns': signature['patterns']})

    # Optional hand-maintained extras (do not override handler declarations).
    if os.path.exists(EXTRAS_FILE):
        with open(EXTRAS_FILE, encoding='utf-8') as fh:
            extras = json.load(fh)
        for mime, handler_name in extras.get('mime_handlers', {}).items():
            mime_handlers.setdefault(mime.lower(), handler_name)
        for name, handler_name in extras.get('detection_handlers', {}).items():
            detection_handlers.setdefault(name.lower(), handler_name)

    _write_json(HANDLERS_FILE, {'mime_handlers': mime_handlers, 'detection_handlers': detection_handlers})
    _write_json(SIGNATURES_FILE, signatures)

    print(f"Wrote {len(mime_handlers)} MIME + {len(detection_handlers)} detection entries "
          f"and {len(signatures)} signatures.")


if __name__ == '__main__':
    main()
