"""Path helpers for the GUI (pure, no Tk)."""
import os


def default_output_dir(source):
    """
    Default extraction directory for a source, mirroring UniExtract's initoutdir:

    - with extension:  <dir>/<stem>            (app.zip -> app)
    - collision:       if <dir>/<stem> already exists as a *file*, dots in the
                       stem become underscores
    - no extension:    <dir>/<name>_extracted  (our CLI's suffix)
    """
    source = str(source)
    directory = os.path.dirname(source)
    base = os.path.basename(source)
    stem, ext = os.path.splitext(base)
    if ext:
        candidate = os.path.join(directory, stem)
        if os.path.isfile(candidate):
            candidate = os.path.join(directory, stem.replace(".", "_"))
        return candidate
    return os.path.join(directory, base + "_extracted")
