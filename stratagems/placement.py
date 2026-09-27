"""Place the radial wheel on the monitor under the cursor.

The window stays at that monitor's center for the whole hold. It is not
repositioned to follow the pointer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import mss


@dataclass(frozen=True)
class Monitor:
    left: int
    top: int
    width: int
    height: int

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x < self.left + self.width and self.top <= y < self.top + self.height

    @property
    def center(self) -> tuple[int, int]:
        return (self.left + self.width // 2, self.top + self.height // 2)


def parse_mss_monitors(entries: Sequence[Mapping[str, int]]) -> list[Monitor]:
    """Turn an mss monitor list into individual screens.

    mss puts the combined virtual desktop at index 0. Centering on that
    rectangle would park the wheel between monitors, so it is skipped.
    """
    monitors: list[Monitor] = []
    for item in entries[1:]:
        width = int(item["width"])
        height = int(item["height"])
        if width < 1 or height < 1:
            continue
        monitors.append(Monitor(int(item["left"]), int(item["top"]), width, height))
    return monitors


def list_monitors() -> list[Monitor]:
    """Monitors reported by the OS screenshot API. Empty when that fails."""
    try:
        with mss.mss() as sct:
            return parse_mss_monitors(sct.monitors)
    except Exception:
        return []


def monitor_for_point(x: int, y: int, monitors: Sequence[Monitor]) -> Monitor:
    """The monitor that contains the point, or the nearest one if none do."""
    if not monitors:
        raise ValueError("monitors must not be empty")
    for monitor in monitors:
        if monitor.contains(x, y):
            return monitor
    return min(monitors, key=lambda monitor: _center_distance_sq(x, y, monitor))


def wheel_top_left(
    x: int,
    y: int,
    monitors: Sequence[Monitor],
    anchor_x: int,
    anchor_y: int,
) -> tuple[int, int]:
    """Top-left of the wheel window so ``(anchor_x, anchor_y)`` sits on the monitor center.

    ``(x, y)`` only chooses the monitor. Two points on the same monitor
    produce the same origin, including monitors that sit left of the primary.
    """
    monitor = monitor_for_point(x, y, monitors)
    center_x, center_y = monitor.center
    return (center_x - anchor_x, center_y - anchor_y)


def format_geometry(width: int, height: int, left: int, top: int) -> str:
    """Tk geometry for an absolute origin, including negative virtual-screen positions.

    A leading minus would measure from the far edge of the primary screen.
    The explicit plus keeps a negative coordinate as an origin offset, which
    is what a monitor to the left of the primary needs.
    """
    return f"{int(width)}x{int(height)}+{int(left)}+{int(top)}"


def _center_distance_sq(x: int, y: int, monitor: Monitor) -> int:
    center_x, center_y = monitor.center
    return (center_x - x) ** 2 + (center_y - y) ** 2
