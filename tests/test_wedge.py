import math

from stratagems.radial_math import aim_endpoint, wedge_index


def _at(angle: float, radius: float = 100.0) -> tuple[float, float]:
    return (radius * math.cos(angle), radius * math.sin(angle))


def test_cardinal_directions_on_four_wedges() -> None:
    deadzone = 20.0
    assert wedge_index(0, -100, 4, deadzone) == 0
    assert wedge_index(100, 0, 4, deadzone) == 1
    assert wedge_index(0, 100, 4, deadzone) == 2
    assert wedge_index(-100, 0, 4, deadzone) == 3


def test_deadzone_and_empty_wheel_cancel() -> None:
    assert wedge_index(0, 0, 8, 20) is None
    assert wedge_index(5, 0, 8, 20) is None
    assert wedge_index(20, 0, 8, 20) is None
    assert wedge_index(21, 0, 4, 20) is not None
    assert wedge_index(100, 0, 0, 20) is None


def test_single_wedge_is_always_the_ring() -> None:
    assert wedge_index(80, -10, 1, 10) == 0
    assert wedge_index(-40, 70, 1, 10) == 0


def test_top_of_a_twelve_wedge_wheel() -> None:
    assert wedge_index(*_at(-math.pi / 2), 12, 10) == 0
    # 20 degrees clockwise of up is still outside wedge 0 (half-width is 15 degrees).
    clockwise = -math.pi / 2 + math.radians(20)
    assert wedge_index(*_at(clockwise), 12, 10) == 1


def test_aim_line_stays_on_the_wheel_while_selection_uses_the_raw_offset() -> None:
    radius = 268.0
    assert aim_endpoint(0, 0, radius) == (0.0, 0.0)
    assert aim_endpoint(40, -30, radius) == (40.0, -30.0)
    assert aim_endpoint(radius, 0, radius) == (radius, 0.0)

    long_dx, long_dy = 800.0, -600.0
    tip_x, tip_y = aim_endpoint(long_dx, long_dy, radius)
    assert math.isclose(math.hypot(tip_x, tip_y), radius)
    assert math.isclose(tip_x / long_dx, radius / 1000)
    assert math.isclose(tip_y / long_dy, radius / 1000)

    assert wedge_index(40, -30, 4, 90) is None
    selected = wedge_index(long_dx, long_dy, 4, 90)
    assert selected is not None
    assert wedge_index(tip_x, tip_y, 4, 90) == selected


def test_just_inside_the_counterclockwise_edge_stays_on_wedge_zero() -> None:
    span = (2 * math.pi) / 4
    angle = -math.pi / 2 - span / 2 + 0.05
    assert wedge_index(*_at(angle), 4, 10) == 0
    outside = -math.pi / 2 - span / 2 - 0.05
    assert wedge_index(*_at(outside), 4, 10) == 3
