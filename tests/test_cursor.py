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
