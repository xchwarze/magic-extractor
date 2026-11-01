"""
Known side effects of the options, shown as a warning alert under an option
while it is in its risky state (e.g. "Fix wrong file extensions" turned on).

Add an entry here whenever an option can surprise the user; the dialogs show
it automatically for any option they render with an alert.
"""

# key -> (values that show the warning, warning text)
OPTION_WARNINGS = {
    # --- Preferences: config.ini [settings] ---------------------------------
    "fix_file_extensions": ((True,), (
        "Renames extracted files that have no extension, guessing the type from "
        "their content. Guesses can be wrong: Makefile, LICENSE or configure become "
        ".txt, an unknown data file may become .docx, and scripts or programs that "
        "expect the exact names can break.")),
    "open_output_folder": ((True,), (
        "Opens an Explorer window for every extracted archive: a folder batch "
        "opens one window per archive.")),
    "check_free_space": ((True,), (
        "Only an estimate (3 x the archive size): it can warn for nothing or miss a "
        "very compressed archive. It only warns; it never stops the extraction.")),
    "create_log_files": ((True,), (
        "Adds magic-extractor.log to every output folder (nested ones too with "
        "Recursive); extracting into the same folder again overwrites it.")),
    "delete_to_recycle_bin": ((False,), (
        "Sources deleted after an extraction are removed permanently, not sent to "
        "the Recycle Bin.")),
    # --- Preferences: gui.ini interface --------------------------------------
    "keep_open": ((False,), (
        "The window closes by itself after every successful run, and its log "
        "goes with it.")),
    "history_enabled": ((True,), (
        "Saves the last 10 source and destination paths in gui.ini.")),
    # --- Run options -----------------------------------------------------------
    "recursive": ((True,), (
        "Also extracts every archive found in the output, up to Max depth: it can "
        "take a long time and a lot of disk (installers often nest many archives), "
        "and the detectors run on every extracted file.")),
    "bruteforce": ((True,), (
        "Runs every detector and tries every handler they map instead of stopping "
        "at the first match: slower, and a handler that does not really fit may "
        "still \"succeed\" with odd output (e.g. 7-Zip unpacking an .exe into its "
        "PE sections).")),
    "fast_check": ((True,), (
        "PureMagic reads only the first 64 KB, so a format recognised by data "
        "further into the file is left to the slower detectors, or missed.")),
    "delete_source": (("delete", "ask"), (
        "The source is deleted after any extraction that reports success, even one "
        "that only got part of a damaged or multi-part archive. Check the output "
        "before relying on it.")),
}


def warning_for(key, value):
    """The warning text for `key` when it has `value`, or None."""
    entry = OPTION_WARNINGS.get(key)
    if entry is None:
        return None
    risky_values, text = entry
    return text if value in risky_values else None
