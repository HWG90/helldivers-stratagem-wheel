"""Windows hides the cursor by driving the ShowCursor counter below zero."""

from stratagems.cursor_pos import conceal_cursor, reveal_cursor
from stratagems.overlay import WS_EX_LAYERED, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW, WS_EX_TOPMOST, WS_EX_TRANSPARENT, overlay_ex_style


def test_show_cursor_false_repeats_until_the_count_is_negative() -> None:
    state = {"count": 2, "false": 0, "true": 0}

    def hide_once() -> int:
        state["false"] += 1
        state["count"] -= 1
        return state["count"]

    steps = conceal_cursor(hide_once)
    assert steps == 3
    assert state["false"] == 3
    assert state["count"] == -1

    def show_once() -> int:
        state["true"] += 1
        state["count"] += 1
        return state["count"]

    reveal_cursor(show_once, steps)
    assert state["true"] == 3
    assert state["count"] == 2


def test_close_balances_only_our_hide_calls() -> None:
    """Do not undo cursor changes owned by another component."""
    state = {"count": 0}

    def hide_once() -> int:
        state["count"] -= 1
        return state["count"]

    def show_once() -> int:
        state["count"] += 1
        return state["count"]

    steps = conceal_cursor(hide_once)
    assert steps == 1
    assert state["count"] == -1
    hide_once()
    hide_once()
    assert state["count"] == -3

    reveal_cursor(show_once, steps)
    assert state["count"] == -2


def test_reveal_without_a_hide_does_not_change_the_count() -> None:
    """Preview and repeated close must leave the display count untouched."""
    state = {"count": -4}

    def show_once() -> int:
        state["count"] += 1
        return state["count"]

    assert reveal_cursor(show_once, 0) == 0
    assert state["count"] == -4


def test_windows_overlay_style_does_not_hit_test_or_activate() -> None:
    style = overlay_ex_style(0x11)
    assert style & WS_EX_LAYERED
    assert style & WS_EX_TRANSPARENT
    assert style & WS_EX_NOACTIVATE
    assert style & WS_EX_TOOLWINDOW
    assert style & WS_EX_TOPMOST
    assert style & 0x11 == 0x11


def test_one_false_is_enough_when_the_cursor_is_already_shown() -> None:
    state = {"count": 0}

    def hide_once() -> int:
        state["count"] -= 1
        return state["count"]

    assert conceal_cursor(hide_once) == 1
    assert state["count"] == -1


def test_repeated_live_holds_preserve_native_settings_cursor():
    import ctypes
    import sys
    import tkinter as tk
    import pytest
    from ctypes import wintypes
    from stratagems.overlay import RadialOverlay, _top_level_hwnd

    if sys.platform != "win32":
        pytest.skip("Win32 cursor regression")
    root = tk.Tk()
    root.withdraw()
    user32 = ctypes.windll.user32
    getter = user32.GetClassLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.GetClassLongW
    getter.argtypes = [wintypes.HWND, ctypes.c_int]
    getter.restype = ctypes.c_void_p
    root.update_idletasks()
    hwnd = _top_level_hwnd(user32, root.winfo_id())
    original_class = getter(hwnd, -12)

    def counter():
        # Balanced probe of this UI thread's counter.
        value = user32.ShowCursor(True) - 1
        user32.ShowCursor(False)
        return value

    initial = counter()
    overlay = RadialOverlay(root, on_confirm=lambda: None, on_cancel=lambda: None)
    try:
        for _ in range(5):
            overlay.set_pointer_locked(True)
            assert counter() == initial  # Not visible yet.
            overlay.show(0, 0, [], "", demo=False, bind_label="Mouse3")
            hidden = counter()
            assert hidden < 0
            assert str(overlay.canvas["cursor"]) == "none"
            overlay.set_transparent(True)
            overlay.set_pointer_locked(True)
            assert counter() == hidden  # No accumulated decrements.
            assert getter(hwnd, -12) == original_class
            overlay.hide()
            overlay.hide()
            assert counter() == initial
            assert getter(hwnd, -12) == original_class
        overlay.show(0, 0, [], "", demo=True, bind_label="Mouse3")
        assert str(overlay.canvas["cursor"]) == "arrow"
        assert counter() == initial
    finally:
        overlay.hide()
        root.destroy()
