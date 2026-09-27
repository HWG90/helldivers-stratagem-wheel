"""Virtual aim offset that keeps the OS cursor parked.

While the radial bind is held, each mouse-move delta is added to an offset
used for wedge selection. The cursor is warped back to the position it had
when the bind went down, so a game camera does not spin, and it is hidden
for the hold. Release warps to that saved point, then shows the cursor.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

CursorGetter = Callable[[], tuple[int, int]]
CursorSetter = Callable[[int, int], None]


class PointerLock:
    def __init__(
        self,
        get_position: CursorGetter,
        set_position: CursorSetter,
        *,
        hide_cursor: Callable[[], None] | None = None,
        show_cursor: Callable[[], None] | None = None,
    ) -> None:
        self._get = get_position
        self._set = set_position
        self._hide_cursor = hide_cursor
        self._show_cursor = show_cursor
        self._mutex = threading.Lock()
        self._anchor: tuple[int, int] | None = None
        self._last: tuple[int, int] = (0, 0)
        self._offset: tuple[int, int] = (0, 0)
        self._busy = False
        self._echo: tuple[int, int] | None = None
        self._cursor_hidden = False

    @property
    def active(self) -> bool:
        with self._mutex:
            return self._anchor is not None

    @property
    def anchor(self) -> tuple[int, int] | None:
        with self._mutex:
            return self._anchor

    @property
    def offset(self) -> tuple[int, int]:
        with self._mutex:
            return self._offset

    def engage(self, fallback: tuple[int, int]) -> tuple[int, int]:
        """Save the absolute cursor position and start a zero offset."""
        try:
            raw_x, raw_y = self._get()
            anchor = (int(raw_x), int(raw_y))
        except Exception:
            anchor = (int(fallback[0]), int(fallback[1]))
        with self._mutex:
            starting = self._anchor is None
            self._anchor = anchor
            self._last = anchor
            self._offset = (0, 0)
            self._echo = None
            self._busy = False
        if starting:
            self._hide_os_cursor()
        return anchor

    def observe(self, x: int, y: int) -> tuple[int, int]:
        """Add the move, then warp the cursor back to the anchor.

        The warp's own mouse event, and a repeat of the point just consumed,
        add nothing. A later move is measured from the anchor, so aiming
        back toward the center shrinks the stored offset.
        """
        sample = (int(x), int(y))
        with self._mutex:
            if self._anchor is None or self._busy:
                return self._offset
            anchor = self._anchor
            if sample == anchor or sample == self._echo:
                return self._offset
            dx = sample[0] - self._last[0]
            dy = sample[1] - self._last[1]
            if dx == 0 and dy == 0:
                return self._offset
            self._offset = (self._offset[0] + dx, self._offset[1] + dy)
            result = self._offset
            self._echo = sample
            # Measure the next real move from the anchor even if the warp
            # event is delivered before this call returns.
            self._last = anchor
            self._busy = True
        landed = self._warp(anchor)
        with self._mutex:
            self._busy = False
            if self._anchor is None:
                return result
            if not landed:
                # The cursor is still on the sample, so the next delta
                # continues from there. There is no warp event to ignore.
                self._last = sample
                self._echo = None
        return result

    def release(self) -> tuple[int, int] | None:
        """Stop tracking and warp to the saved point. None when nothing was held."""
        with self._mutex:
            if self._anchor is None:
                return None
            offset = self._offset
            anchor = self._anchor
            self._anchor = None
            self._offset = (0, 0)
            self._last = (0, 0)
            self._echo = None
            self._busy = False
            show = self._cursor_hidden
            self._cursor_hidden = False
        self._warp(anchor)
        if show:
            self._show_os_cursor()
        return offset

    def _hide_os_cursor(self) -> None:
        callback = self._hide_cursor
        if callback is None:
            return
        with self._mutex:
            if self._cursor_hidden or self._anchor is None:
                return
            self._cursor_hidden = True
        try:
            callback()
        except Exception:
            with self._mutex:
                self._cursor_hidden = False

    def _show_os_cursor(self) -> None:
        callback = self._show_cursor
        if callback is None:
            return
        try:
            callback()
        except Exception:
            return

    def _warp(self, anchor: tuple[int, int]) -> bool:
        try:
            self._set(anchor[0], anchor[1])
        except Exception:
            return False
        return True
