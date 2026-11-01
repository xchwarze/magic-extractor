"""Binwalk fragment listing and carving workflow."""

import argparse
import logging
import os
import pathlib

from cli_paths import BIN_PATH
from detection_filter import is_generic_detection
from extraction import process_extraction
from file_type import binwalk_file_map
from formats import get_handlers_from_detection
from helpers import run_per_file


_COPY_CHUNK = 1 << 20


def _copy_range(source_fh, offset, size, destination):
    """Copy size bytes from offset of an open file to destination, in chunks
    (never the whole input in memory)."""
    source_fh.seek(offset)
    remaining = size
    with open(destination, "wb") as carved_fh:
        while remaining > 0:
            chunk = source_fh.read(min(_COPY_CHUNK, remaining))
            if not chunk:
                break
            carved_fh.write(chunk)
            remaining -= len(chunk)


def process_carve(args):
    """Carve a file, or each file of a directory (one at a time)."""
    return run_per_file(args, _carve_file, output_name=lambda item, _items: f"{item.name}_carved")


def _carve_file(args):
    """List or carve embedded blobs at offsets reported by binwalk."""
    entries = binwalk_file_map(args.file_path, BIN_PATH)
    if not entries:
        logging.error(f"Binwalk found nothing to carve in {args.file_path}")
        return False

    if getattr(args, "list_fragments", False):
        print(f"{'IDX':>3}  {'OFFSET':>10}  {'SIZE':>12}  {'NAME':<20}  DESCRIPTION")
        print(f"{'-' * 3}  {'-' * 10}  {'-' * 12}  {'-' * 20}  {'-' * 11}")
        for index, entry in enumerate(entries):
            offset = entry.get("offset", 0) or 0
            size = entry.get("size", 0) or 0
            name = entry.get("name") or ""
            description = entry.get("description") or ""
            print(
                f"{index:>3}  {offset:#010x}  {size:>12,}  "
                f"{name:<20.20}  {description}"
            )
        print(f"\n{len(entries)} fragment(s).")
        return True

    if args.fragment is not None:
        if not 0 <= args.fragment < len(entries):
            logging.error(
                f"Fragment index {args.fragment} out of range (0..{len(entries) - 1})"
            )
            return False
        selected = [(args.fragment, entries[args.fragment])]
    else:
        selected = list(enumerate(entries))

    carve_all = args.raw or args.fragment is not None
    output_dir = str(args.output_dir) if args.output_dir else f"{args.file_path}_carved"
    try:
        os.makedirs(output_dir, exist_ok=True)
        source_fh = open(args.file_path, "rb")
    except OSError as exc:
        logging.error(f"Cannot carve {args.file_path} into {output_dir}: {exc}")
        return False
    with source_fh:
        return _carve_entries(args, source_fh, selected, carve_all, output_dir)


def _carve_entries(args, source_fh, selected, carve_all, output_dir):
    """Carve the selected binwalk entries out of source_fh and extract the ones with a handler."""
    carved_any = False
    extractions_ok = True
    for index, entry in selected:
        name = (entry.get("name") or "").lower()
        offset = entry.get("offset", 0) or 0
        size = entry.get("size") or 0
        if size <= 0:
            continue

        has_handler = bool(get_handlers_from_detection(name)) and not is_generic_detection(
            name
        )
        if not carve_all and not has_handler:
            continue

        carved_path = os.path.join(
            output_dir, f"carved_{index}_{offset}_{name}.bin"
        )
        try:
            _copy_range(source_fh, offset, size, carved_path)
        except OSError as exc:
            logging.error(f"Could not write carved [{index}] {name} to {carved_path}: {exc}")
            extractions_ok = False
            continue
        logging.info(
            f"Carved [{index}] {name} at offset {offset} ({size} bytes) -> "
            f"{carved_path}"
        )
        carved_any = True

        if has_handler:
            nested_args = argparse.Namespace(
                file_path=pathlib.Path(carved_path),
                output_dir=None,
                fast_check=args.fast_check,
                password=getattr(args, "password", None),
                recursive=False,
                open_output_folder=False,
            )
            if not process_extraction(nested_args):
                extractions_ok = False
                logging.error(f"Carved [{index}] {name} could not be extracted: {carved_path}")

    if not carved_any:
        logging.error(f"No matching data to carve in {args.file_path}")
    # Success means everything with a handler was carved AND extracted.
    return carved_any and extractions_ok
