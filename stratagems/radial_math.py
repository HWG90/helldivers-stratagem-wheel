"""Map a pointer offset to a radial-menu wedge.

Wedge 0 is centered on screen-up. Wedges proceed clockwise. Coordinates use
screen space: +x right, +y down. The center deadzone cancels.
"""

from __future__ import annotations

import math


def wedge_index(dx: float, dy: float, count: int, deadzone: float) -> int | None:
    if count <= 0:
        return None
    if math.hypot(dx, dy) <= deadzone:
        return None
    span = (2 * math.pi) / count
    angle = math.atan2(dy, dx)
    offset_from_up = (angle + math.pi / 2) % (2 * math.pi)
    adjusted = (offset_from_up + span / 2) % (2 * math.pi)
    return int(adjusted / span) % count


def wedge_center_angle(index: int, count: int) -> float:
    """Screen angle (0 = east, clockwise positive) at the middle of a wedge."""
    if count <= 0:
        raise ValueError("count must be positive")
    span = (2 * math.pi) / count
    return index * span - math.pi / 2
