"""Whether Helldivers 2 owns the foreground window.

The radial bind is global. The wheel opens only while ``helldivers2.exe`` is
the foreground process, so a hold in another program does not hide the cursor
or raise the overlay. The terminal Preview button does not use this check.
"""

from __future__ import annotations

import sys

_GAME_EXE = "helldivers2.exe"
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def is_helldivers_process(image: str | None) -> bool:
    """True when ``image`` is the Helldivers 2 executable, with or without a path."""
    if not image:
        return False
    name = image.replace("\\", "/").rsplit("/", 1)[-1]
    return name.casefold() == _GAME_EXE


def foreground_image() -> str | None:
    """Full image path of the foreground process, or None when it cannot be read."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        return buffer.value or None
    finally:
        kernel32.CloseHandle(handle)


def helldivers_focused() -> bool:
    """True when the foreground window belongs to Helldivers 2."""
    try:
        return is_helldivers_process(foreground_image())
    except OSError:
        return False
