"""Windows hides the cursor by driving the ShowCursor counter below zero."""

from stratagems.cursor_pos import conceal_cursor, reveal_cursor


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


def test_one_false_is_enough_when_the_cursor_is_already_shown() -> None:
    state = {"count": 0}

    def hide_once() -> int:
        state["count"] -= 1
        return state["count"]

    assert conceal_cursor(hide_once) == 1
    assert state["count"] == -1
