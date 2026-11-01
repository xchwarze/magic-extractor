import os
import logging
import argparse
import pathlib


def run_per_file(args, process, output_name=None):
    """
    Run ``process(args)`` on ``args.file_path``, or once per file when it is a
    directory (non-recursive, sorted). Detectors and extractors only ever get
    one file at a time, never the directory itself.

    ``output_name(item, items) -> str``: each file of the directory gets its
    own ``<base>/<output_name(item, items)>`` folder, where ``base`` is
    ``args.output_dir`` or else the file's own folder, so no two files of the
    directory write into the same one. ``items`` are all the files of the run.

    Returns True only if every file succeeded.
    """
    if not os.path.isdir(args.file_path):
        return process(args)

    items = [item for item in sorted(pathlib.Path(args.file_path).iterdir()) if item.is_file()]
    if not items:
        # Subfolders are not processed; an empty run is a failure, not a silent 0.
        logging.error(f"No files to process in {args.file_path} (subfolders are not processed)")
        return False
    all_ok = True
    for item in items:
        logging.info(f"Processing file: {item}")
        item_args = argparse.Namespace(**vars(args))
        item_args.file_path = item
        if output_name:
            output_dir = getattr(args, "output_dir", None)
            base = pathlib.Path(output_dir) if output_dir else item.parent
            item_args.output_dir = base / output_name(item, items)
        if not process(item_args):
            all_ok = False
            logging.error(f"Failed for file: {item}")
    return all_ok

def delete_source(path, use_recycle_bin=True):
    """
    Delete a source file after a successful extraction.

    Recycle Bin by default (recoverable). If the Recycle Bin is requested but
    send2trash is unavailable, the file is KEPT (never silently permanently
    deleted). Returns True if the file was removed, False if kept/failed.
    """
    path = str(path)
    if use_recycle_bin:
        try:
            from send2trash import send2trash
        except ImportError:
            logging.warning(f"send2trash unavailable; keeping source (not permanently deleting): {path}")
            return False
        try:
            send2trash(path)
            logging.info(f"Source moved to Recycle Bin: {path}")
            return True
        except OSError as exc:
            logging.error(f"Could not recycle source {path}: {exc}")
            return False

    try:
        os.remove(path)
        logging.info(f"Source permanently deleted: {path}")
        return True
    except OSError as exc:
        logging.error(f"Could not delete source {path}: {exc}")
        return False
