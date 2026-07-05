"""Recent-items history (pure, no Tk). Stored pipe-joined in gui.ini [history]."""


def parse(raw):
    """Pipe-joined string -> list, dropping empties."""
    if not raw:
        return []
    return [part for part in raw.split("|") if part]


def join(items):
    """List -> pipe-joined string."""
    return "|".join(items)


def push(items, value, max_entries):
    """Prepend value (deduped, most-recent first), capped at max_entries."""
    value = (value or "").strip()
    if not value:
        return list(items)
    out = [value] + [item for item in items if item != value]
    return out[:max_entries]
