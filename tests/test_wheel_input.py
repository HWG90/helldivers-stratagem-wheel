"""Wheel placement is the monitor center. Aiming is a summed mouse delta."""

from stratagems.overlay import WHEEL_X, WHEEL_Y
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
