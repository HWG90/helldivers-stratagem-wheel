"""Ordinary OS cursor get and set.

Windows uses ``GetCursorPos`` / ``SetCursorPos``. Linux uses X11
``XQueryPointer`` / ``XWarpPointer`` on our own display connection, so a
warp from the mouse listener does not take pynput's lock. Other platforms
use pynput's controller, which is the same class of cursor API. Nothing
here injects into another process.
"""

from __future__ import annotations

import atexit
import ctypes
import ctypes.util
import sys
import threading
from collections.abc import Callable
from ctypes import wintypes

from pynput.mouse import Controller


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


_SHOW_CURSOR_LIMIT = 64


def conceal_cursor(hide_once: Callable[[], int]) -> int:
    """Call ShowCursor(FALSE) until the display count is negative.

    The counter is sticky. One FALSE leaves the cursor visible when the
    count started above zero.
    """
    steps = 0
    while steps < _SHOW_CURSOR_LIMIT:
        count = int(hide_once())
        steps += 1
        if count < 0:
            return steps
    return steps


def reveal_cursor(show_once: Callable[[], int], steps: int) -> None:
    """Undo the FALSE calls from ``conceal_cursor`` and no more."""
    for _ in range(max(0, steps)):
        show_once()


class _Win32Cursor:
    def __init__(self) -> None:
        self._user32 = ctypes.windll.user32
        self._user32.GetCursorPos.argtypes = [ctypes.POINTER(_POINT)]
        self._user32.GetCursorPos.restype = wintypes.BOOL
        self._user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        self._user32.SetCursorPos.restype = wintypes.BOOL
        self._user32.ShowCursor.argtypes = [wintypes.BOOL]
        self._user32.ShowCursor.restype = ctypes.c_int
        self._visible = True
        self._restore_steps = 0

    def hide(self) -> None:
        if not self._visible:
            return
        self._restore_steps = conceal_cursor(lambda: int(self._user32.ShowCursor(False)))
        self._visible = False

    def show(self) -> None:
        if self._visible:
            return
        reveal_cursor(lambda: int(self._user32.ShowCursor(True)), self._restore_steps)
        self._restore_steps = 0
        self._visible = True

    def get(self) -> tuple[int, int]:
        point = _POINT()
        if not self._user32.GetCursorPos(ctypes.byref(point)):
            raise OSError("GetCursorPos failed")
        return int(point.x), int(point.y)

    def set(self, x: int, y: int) -> None:
        if not self._user32.SetCursorPos(int(x), int(y)):
            raise OSError("SetCursorPos failed")


class _X11Cursor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        lib_name = ctypes.util.find_library("X11") or "libX11.so.6"
        self._x11 = ctypes.CDLL(lib_name)
        self._x11.XOpenDisplay.restype = ctypes.c_void_p
        self._x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        display = self._x11.XOpenDisplay(None)
        if not display:
            raise OSError("XOpenDisplay failed")
        self._display = display
        self._x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self._x11.XDefaultRootWindow.restype = ctypes.c_ulong
        self._root = self._x11.XDefaultRootWindow(self._display)
        self._x11.XWarpPointer.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_int,
        ]
        self._x11.XWarpPointer.restype = ctypes.c_int
        self._x11.XFlush.argtypes = [ctypes.c_void_p]
        self._x11.XFlush.restype = ctypes.c_int
        self._x11.XQueryPointer.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_uint),
        ]
        self._x11.XQueryPointer.restype = ctypes.c_int
        self._xfixes = None
        self._visible = True
        fixes_name = ctypes.util.find_library("Xfixes") or "libXfixes.so.3"
        try:
            fixes = ctypes.CDLL(fixes_name)
            fixes.XFixesHideCursor.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            fixes.XFixesHideCursor.restype = None
            fixes.XFixesShowCursor.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            fixes.XFixesShowCursor.restype = None
        except (OSError, AttributeError):
            fixes = None
        self._xfixes = fixes

    def hide(self) -> None:
        if self._xfixes is None or not self._visible:
            return
        with self._lock:
            self._xfixes.XFixesHideCursor(self._display, self._root)
            self._x11.XFlush(self._display)
        self._visible = False

    def show(self) -> None:
        if self._xfixes is None or self._visible:
            return
        with self._lock:
            self._xfixes.XFixesShowCursor(self._display, self._root)
            self._x11.XFlush(self._display)
        self._visible = True

    def get(self) -> tuple[int, int]:
        root = ctypes.c_ulong()
        child = ctypes.c_ulong()
        root_x = ctypes.c_int()
        root_y = ctypes.c_int()
        win_x = ctypes.c_int()
        win_y = ctypes.c_int()
        mask = ctypes.c_uint()
        with self._lock:
            ok = self._x11.XQueryPointer(
                self._display,
                self._root,
                ctypes.byref(root),
                ctypes.byref(child),
                ctypes.byref(root_x),
                ctypes.byref(root_y),
                ctypes.byref(win_x),
                ctypes.byref(win_y),
                ctypes.byref(mask),
            )
        if not ok:
            raise OSError("XQueryPointer failed")
        return int(root_x.value), int(root_y.value)

    def set(self, x: int, y: int) -> None:
        with self._lock:
            self._x11.XWarpPointer(self._display, 0, self._root, 0, 0, 0, 0, int(x), int(y))
            self._x11.XFlush(self._display)


class _PynputCursor:
    def __init__(self) -> None:
        self._mouse = Controller()
        self._lock = threading.Lock()

    def get(self) -> tuple[int, int]:
        with self._lock:
            x, y = self._mouse.position
        return int(x), int(y)

    def set(self, x: int, y: int) -> None:
        with self._lock:
            self._mouse.position = (int(x), int(y))

    def hide(self) -> None:
        return

    def show(self) -> None:
        return


_backend: _Win32Cursor | _X11Cursor | _PynputCursor | None = None
_backend_lock = threading.Lock()


def get_cursor() -> tuple[int, int]:
    return _cursor().get()


def set_cursor(x: int, y: int) -> None:
    _cursor().set(x, y)


def hide_cursor() -> None:
    """Hide the OS cursor. A second call does nothing until ``show_cursor``.

    On Windows the hide repeats ShowCursor(FALSE) until the display count
    is negative, then show restores that many TRUE calls.
    """
    global _cursor_hidden
    with _visibility_lock:
        if _cursor_hidden:
            return
        _cursor().hide()
        _cursor_hidden = True


def show_cursor() -> None:
    """Show the OS cursor if this process hid it. Safe to call when it is already shown."""
    global _cursor_hidden
    with _visibility_lock:
        if not _cursor_hidden:
            return
        _cursor().show()
        _cursor_hidden = False


def _show_cursor_on_exit() -> None:
    try:
        show_cursor()
    except Exception:
        return


_cursor_hidden = False
_visibility_lock = threading.Lock()
atexit.register(_show_cursor_on_exit)


def _cursor() -> _Win32Cursor | _X11Cursor | _PynputCursor:
    global _backend
    with _backend_lock:
        if _backend is None:
            _backend = _open_cursor()
        return _backend


def _open_cursor() -> _Win32Cursor | _X11Cursor | _PynputCursor:
    if sys.platform == "win32":
        return _Win32Cursor()
    if sys.platform.startswith("linux"):
        try:
            return _X11Cursor()
        except (OSError, AttributeError):
            return _PynputCursor()
    return _PynputCursor()
