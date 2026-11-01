"""Helpers shared by the GUI's dialogs."""


def bind_default(window, action):
    """Enter presses the focused button; with focus elsewhere it runs ``action``.

    ``action`` is the dialog's default (primary) button. A focused button always wins:
    Enter on Cancel must cancel, not save. A multi-line Text keeps Enter for new lines.
    Returns the handler (also stored as ``window.return_handler``).
    """

    def on_return(event):
        widget = event.widget
        widget_class = widget.winfo_class() if hasattr(widget, "winfo_class") else ""
        if widget_class == "Text":
            return None
        if widget_class in ("TButton", "Button"):
            widget.invoke()
        else:
            action()
        return "break"

    window.bind("<Return>", on_return)
    window.return_handler = on_return
    return on_return
