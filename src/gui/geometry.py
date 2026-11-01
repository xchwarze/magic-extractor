"""Where a window may go: display scaling and the usable screen area.

Tk positions the outer frame of a toplevel but sizes only its client area, so every
placement here budgets for the frame (borders and title bar) as well. Nothing in this
module opens a window, so the pure helpers are testable without a display.
"""
import re
import sys
import tkinter as tk

# Never open a dialog larger than this share of the screen.
MAX_SCREEN_SHARE = 0.9

# Tk reports WIDTHxHEIGHT+X+Y where X and Y may be negative (a monitor left of or above the
# primary one), written "+-1800".
_GEOMETRY = re.compile(r"^(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)$")
# How much of a window must stay reachable on screen so its title bar can still be grabbed.
_VISIBLE_WIDTH = 120
_VISIBLE_HEIGHT = 40


def dpi_scale(widget):
    """Ratio of the current Tk scaling to 96 DPI (1.0 at 100%)."""
    try:
        return float(widget.winfo_fpixels("1i")) / 96.0
    except tk.TclError:
        return 1.0


def scaled(widget, pixels):
    """A 96 DPI pixel size converted for this display's scaling."""
    return round(pixels * dpi_scale(widget))


def work_area(window, near=None):
    """Usable screen rectangle (left, top, right, bottom) without the taskbar.

    On Windows this is the work area of the monitor showing ``near`` (or the window
    itself); elsewhere, or when the query fails, the whole screen.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class MonitorInfo(ctypes.Structure):
                _fields_ = (
                    ("cbSize", wintypes.DWORD),
                    ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD),
                )

            target = near if near is not None else window
            # A private WinDLL: setting prototypes on the shared ``ctypes.windll.user32``
            # would change them for every other caller in the process.
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.GetParent.restype = wintypes.HWND
            user32.GetParent.argtypes = (wintypes.HWND,)
            user32.MonitorFromWindow.restype = wintypes.HANDLE
            user32.MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)
            user32.GetMonitorInfoW.argtypes = (wintypes.HANDLE, ctypes.POINTER(MonitorInfo))
            # Tk's winfo_id is the client child; the monitor lookup wants the frame. The
            # explicit prototypes matter: ctypes' default c_int truncates 64-bit handles.
            hwnd = user32.GetParent(target.winfo_id()) or target.winfo_id()
            monitor = user32.MonitorFromWindow(hwnd, 1)  # MONITOR_DEFAULTTOPRIMARY
            info = MonitorInfo()
            info.cbSize = ctypes.sizeof(MonitorInfo)
            if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                work = info.rcWork
                return work.left, work.top, work.right, work.bottom
        except (OSError, AttributeError, tk.TclError):
            pass  # fall back to the whole screen below
    return 0, 0, int(window.winfo_screenwidth()), int(window.winfo_screenheight())


def frame_extras(window):
    """Pixels the window manager adds around a mapped toplevel: (side/bottom border, title bar).

    (0, 0) until the window has been given a position, and also when the two positions
    disagree wildly (a withdrawn window keeps a stale outer position): no frame is that big.
    """
    border = max(0, window.winfo_rootx() - window.winfo_x())
    title = max(0, window.winfo_rooty() - window.winfo_y())
    limit = 200 * max(1.0, dpi_scale(window))
    if border > limit or title > limit:
        return 0, 0
    return border, title


def clamp_into(x, y, width, height, area, extras=(0, 0)):
    """The position nearest (x, y) that keeps a width x height client area, plus its frame, in ``area``.

    ``area`` is (left, top, right, bottom); ``extras`` is (border, title bar) from
    :func:`frame_extras`. A window larger than the area is pinned to its top-left corner.
    """
    left, top, right, bottom = area
    border, title = extras
    x = min(max(left, x), max(left, right - width - 2 * border))
    y = min(max(top, y), max(top, bottom - height - title - border))
    return x, y


def fit_size(width, height, area, extras=(0, 0)):
    """``width`` x ``height`` reduced, when needed, to fit the share of ``area`` a dialog may use."""
    left, top, right, bottom = area
    border, title = extras
    max_width = min(int((right - left) * MAX_SCREEN_SHARE), right - left - 2 * border)
    max_height = min(int((bottom - top) * MAX_SCREEN_SHARE), bottom - top - title - border)
    return min(width, max_width), min(height, max_height)


def parse_geometry(text):
    """``(width, height, x, y)`` from a Tk ``WxH+X+Y`` string, or None when it is not one."""
    match = _GEOMETRY.match(text.strip()) if isinstance(text, str) else None
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)),
            _coordinate(match.group(3)), _coordinate(match.group(4)))


def _coordinate(text):
    """One coordinate of a geometry string: ``+120``, ``+-1800`` (left of the primary) or ``-5``."""
    number = int(text[1:])
    return number if text[0] == "+" else -number


def visible_position(position, size, screen):
    """The saved position kept on screen, or None when it lies outside every monitor.

    ``screen`` is the virtual desktop (left, top, right, bottom). A monitor unplugged since
    the last run leaves the saved point outside it, and opening there would hide the window.
    Inside the desktop the position is nudged so the title bar stays reachable.
    """
    left, top, right, bottom = screen
    x, y = position
    width, height = size
    if not (left - width < x < right and top <= y < bottom):
        return None
    x = min(max(x, left - width + _VISIBLE_WIDTH), right - _VISIBLE_WIDTH)
    y = min(max(y, top), bottom - _VISIBLE_HEIGHT)
    return x, y
