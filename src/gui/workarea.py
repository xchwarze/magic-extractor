"""Display scaling and the usable screen area, for popups that must stay on screen."""
import sys
import tkinter as tk

from gui.icons import dpi_scale


def scaled(widget, pixels):
    """A size given in 96 DPI pixels converted for this display's scaling."""
    return round(pixels * dpi_scale(widget))


def work_area(window, near=None):
    """Usable screen rectangle ``(left, top, right, bottom)``, taskbar excluded.

    On Windows it is the work area of the monitor showing ``near`` (default: the window
    itself), in virtual-screen coordinates (a monitor left of or above the primary one has
    negative ones). Elsewhere, or if the query fails, it is the whole screen.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class MonitorInfo(ctypes.Structure):
                _fields_ = (("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                            ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD))

            target = near if near is not None else window
            # A private WinDLL: ctypes.windll.user32 is shared process-wide, so prototypes set
            # on it would change every other caller's.
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.GetParent.restype = wintypes.HWND
            user32.GetParent.argtypes = (wintypes.HWND,)
            user32.MonitorFromWindow.restype = wintypes.HANDLE
            user32.MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)
            user32.GetMonitorInfoW.argtypes = (wintypes.HANDLE, ctypes.POINTER(MonitorInfo))
            # winfo_id is the client child; the monitor lookup wants the frame HWND. The
            # explicit prototypes matter: the default c_int would truncate 64-bit handles.
            hwnd = user32.GetParent(target.winfo_id()) or target.winfo_id()
            monitor = user32.MonitorFromWindow(hwnd, 1)  # MONITOR_DEFAULTTOPRIMARY
            info = MonitorInfo()
            info.cbSize = ctypes.sizeof(MonitorInfo)
            if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                work = info.rcWork
                return work.left, work.top, work.right, work.bottom
        except (OSError, AttributeError, tk.TclError):
            pass  # fall back to the whole screen
    return 0, 0, int(window.winfo_screenwidth()), int(window.winfo_screenheight())


def clamp_into(x, y, width, height, area):
    """The top-left that keeps a ``width`` x ``height`` box inside ``area`` (top-left wins if too big)."""
    left, top, right, bottom = area
    return min(max(left, x), max(left, right - width)), min(max(top, y), max(top, bottom - height))
