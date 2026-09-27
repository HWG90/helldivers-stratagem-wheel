"""Wheel placement is the monitor center. Aiming is a summed mouse delta."""

import math
import tkinter as tk

from stratagems.catalog import LoadoutEntry
from stratagems.overlay import OUTER, WHEEL_X, WHEEL_Y, RadialOverlay
from stratagems.placement import Monitor, format_geometry, parse_mss_monitors, wheel_top_left
from stratagems.pointer_lock import PointerLock
from stratagems.radial_math import wedge_index

PRIMARY = Monitor(0, 0, 1920, 1080)
SIDE = Monitor(1920, -200, 2560, 1440)
LEFT = Monitor(-1280, 80, 1280, 1024)
ANCHOR_X = WHEEL_X
ANCHOR_Y = WHEEL_Y


def _origin(x: int, y: int) -> tuple[int, int]:
    return wheel_top_left(x, y, (PRIMARY, SIDE, LEFT), ANCHOR_X, ANCHOR_Y)


def _center_of(origin: tuple[int, int]) -> tuple[int, int]:
    return (origin[0] + ANCHOR_X, origin[1] + ANCHOR_Y)


def test_wheel_centers_on_the_monitor_under_the_cursor() -> None:
    on_primary = _origin(120, 400)
    elsewhere_on_primary = _origin(1900, 1079)
    assert on_primary == elsewhere_on_primary
    assert _center_of(on_primary) == PRIMARY.center

    on_side = _origin(2000, 10)
    assert on_side == _origin(1920 + 2560 - 1, -200)
    assert _center_of(on_side) == SIDE.center

    on_left = _origin(-10, 100)
    assert _center_of(on_left) == LEFT.center
    assert on_left[0] < 0
    assert format_geometry(800, 800, on_left[0], on_left[1]).startswith("800x800+-")


def test_shared_edge_belongs_to_the_monitor_that_starts_there() -> None:
    assert _center_of(_origin(1920, 100)) == SIDE.center
    assert _center_of(_origin(1919, 100)) == PRIMARY.center


def test_mss_virtual_desktop_is_not_a_placement_target() -> None:
    monitors = parse_mss_monitors(
        (
            {"left": -1280, "top": 0, "width": 3200, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": -1280, "top": 0, "width": 1280, "height": 1024},
        )
    )
    assert monitors == [PRIMARY, Monitor(-1280, 0, 1280, 1024)]


def test_deltas_accumulate_across_a_warp_back_and_release_restores_the_anchor() -> None:
    cursor = {"x": 400, "y": 300}

    def get_position() -> tuple[int, int]:
        return (cursor["x"], cursor["y"])

    def set_position(x: int, y: int) -> None:
        cursor["x"] = x
        cursor["y"] = y

    lock = PointerLock(get_position, set_position)
    assert lock.engage((0, 0)) == (400, 300)
    assert lock.offset == (0, 0)

    cursor["x"] = 460
    cursor["y"] = 280
    assert lock.observe(460, 280) == (60, -20)
    assert (cursor["x"], cursor["y"]) == (400, 300)

    assert lock.observe(400, 300) == (60, -20)
    assert (cursor["x"], cursor["y"]) == (400, 300)

    assert lock.observe(430, 340) == (90, 20)
    assert (cursor["x"], cursor["y"]) == (400, 300)
    assert wedge_index(90, 20, 4, 90) == 1

    cursor["x"] = 510
    cursor["y"] = 330
    assert lock.release() == (90, 20)
    assert (cursor["x"], cursor["y"]) == (400, 300)
    assert lock.release() is None
    assert not lock.active


def test_a_failed_warp_does_not_apply_the_same_delta_twice() -> None:
    def get_position() -> tuple[int, int]:
        return (10, 10)

    def set_position(x: int, y: int) -> None:
        raise OSError("cursor rejected")

    lock = PointerLock(get_position, set_position)
    lock.engage((10, 10))
    assert lock.observe(25, 10) == (15, 0)
    assert lock.observe(40, 18) == (30, 8)
    assert lock.release() == (30, 8)


def test_hold_hides_the_cursor_and_release_warps_then_shows_it() -> None:
    cursor = {"x": 400, "y": 300}
    events: list[tuple[object, ...]] = []

    def get_position() -> tuple[int, int]:
        return (cursor["x"], cursor["y"])

    def set_position(x: int, y: int) -> None:
        cursor["x"] = x
        cursor["y"] = y
        events.append(("warp", x, y))

    def hide() -> None:
        events.append(("hide", cursor["x"], cursor["y"]))

    def show() -> None:
        events.append(("show", cursor["x"], cursor["y"]))

    lock = PointerLock(get_position, set_position, hide_cursor=hide, show_cursor=show)
    assert lock.engage((0, 0)) == (400, 300)
    assert events == [("hide", 400, 300)]

    lock.engage((1, 1))
    assert events == [("hide", 400, 300)]

    cursor["x"] = 460
    cursor["y"] = 280
    assert lock.observe(460, 280) == (60, -20)
    assert events == [("hide", 400, 300), ("warp", 400, 300)]
    assert (cursor["x"], cursor["y"]) == (400, 300)

    cursor["x"] = 510
    cursor["y"] = 330
    assert lock.release() == (60, -20)
    assert events[-2] == ("warp", 400, 300)
    assert events[-1] == ("show", 400, 300)
    assert (cursor["x"], cursor["y"]) == (400, 300)
    assert lock.release() is None
    assert events[-1] == ("show", 400, 300)


def test_release_shows_the_cursor_after_a_failed_warp() -> None:
    events: list[str] = []

    def get_position() -> tuple[int, int]:
        return (8, 9)

    def set_position(x: int, y: int) -> None:
        events.append("warp")
        raise OSError("cursor rejected")

    lock = PointerLock(
        get_position,
        set_position,
        hide_cursor=lambda: events.append("hide"),
        show_cursor=lambda: events.append("show"),
    )
    lock.engage((0, 0))
    assert lock.release() == (0, 0)
    assert events == ["hide", "warp", "show"]
    assert lock.release() is None
    assert events == ["hide", "warp", "show"]


def test_aim_line_on_the_wheel_tracks_the_offset_and_is_not_a_cursor() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        overlay = RadialOverlay(root, on_confirm=lambda: None, on_cancel=lambda: None)
        overlay.show(
            0,
            0,
            [
                LoadoutEntry("Up", ("up",), "sample"),
                LoadoutEntry("Right", ("right",), "sample"),
                LoadoutEntry("Down", ("down",), "sample"),
                LoadoutEntry("Left", ("left",), "sample"),
            ],
            "",
            demo=True,
            bind_label="Mouse3",
        )
        overlay.apply_offset(1000, 0)
        assert overlay.highlight == 1
        kinds = [overlay.canvas.type(item) for item in overlay.canvas.find_withtag("aim")]
        assert kinds == ["line", "line", "oval"]
        x0, y0, x1, y1 = overlay.canvas.coords(overlay.canvas.find_withtag("aim")[0])
        assert math.isclose(x0, WHEEL_X)
        assert math.isclose(y0, WHEEL_Y)
        assert math.isclose(math.hypot(x1 - x0, y1 - y0), OUTER)

        overlay.apply_offset(1000, 0)
        assert overlay.highlight == 1

        overlay.apply_offset(30, 0)
        assert overlay.highlight is None
        _x0, _y0, x1, y1 = overlay.canvas.coords(overlay.canvas.find_withtag("aim")[0])
        assert math.isclose(math.hypot(x1 - WHEEL_X, y1 - WHEEL_Y), 30)

        overlay.apply_offset(0, 0)
        assert overlay.canvas.find_withtag("aim") == ()
        overlay.set_pointer_locked(True)
        assert str(overlay.canvas["cursor"]) == "none"
        overlay.hide()
        assert overlay.canvas.find_withtag("aim") == ()
    finally:
        root.destroy()
