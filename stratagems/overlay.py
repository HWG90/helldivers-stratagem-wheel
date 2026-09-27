"""Frameless, always-on-top radial wheel."""

from __future__ import annotations

import ctypes
import math
import sys
import tkinter as tk
from collections.abc import Callable
from ctypes import wintypes

from stratagems.arrows import format_code
from stratagems.cursor_pos import keep_cursor_hidden, show_cursor
from stratagems.catalog import LoadoutEntry
from stratagems.matching import short_alias
from stratagems.placement import format_geometry
from stratagems.radial_math import aim_endpoint, wedge_center_angle, wedge_index
from stratagems.theme import BG, BLACK, BODY_CANDIDATES, MUTED, TITLE_CANDIDATES, WHITE, YELLOW, pick_family
from stratagems.widgets import paint_hazard_border

SIZE = 800
# The drawn wheel sits below the title, not on the window's geometric center.
WHEEL_X = SIZE // 2
WHEEL_Y = 430
OUTER = 268
INNER = 102
DEADZONE = 90
# Windows color key. It is not black, so labels and the center readout stay painted.
TRANSPARENT_KEY = "#ff00ff"
# Extended styles for a borderless topmost overlay that does not hit-test the mouse.
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
_OVERLAY_EXSTYLE = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST
_COLOR_KEY_REF = 0x00FF00FF
_LWA_COLORKEY = 0x00000001
_LWA_ALPHA = 0x00000002


class RadialOverlay:
    def __init__(
        self,
        root: tk.Tk,
        *,
        on_confirm: Callable[[], None],
        on_cancel: Callable[[], None],
    ) -> None:
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.family = pick_family(BODY_CANDIDATES)
        self.title_family = pick_family(TITLE_CANDIDATES)
        self.entries: list[LoadoutEntry] = []
        self.notice = ""
        self.demo = False
        self.bind_label = "Mouse3 (middle)"
        self.highlight: int | None = None
        self.visible = False
        self.pointer_locked = False
        self.transparent = False
        self._aim = (0.0, 0.0)
        self.external_bind = False
        self.center_screen = (0, 0)
        self.deadzone = DEADZONE

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.configure(bg=BG)
        self.win.withdraw()
        try:
            self.win.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.canvas = tk.Canvas(self.win, width=SIZE, height=SIZE, bg=BG, highlightthickness=0, bd=0, cursor="none")
        self.canvas.pack()
        self._blank_cursor()
        self.canvas.bind("<ButtonRelease-1>", self._on_left)
        self.canvas.bind("<ButtonRelease-2>", self._on_middle)
        self.win.bind("<Escape>", lambda _event: self.on_cancel())

    def show(
        self,
        left: int,
        top: int,
        entries: list[LoadoutEntry],
        notice: str,
        *,
        demo: bool,
        bind_label: str,
    ) -> None:
        self.entries = list(entries)
        self.notice = notice
        self.demo = demo
        self.bind_label = bind_label
        self.highlight = None
        self._aim = (0.0, 0.0)
        self._place(left, top)
        self.visible = True
        self.win.deiconify()
        self.win.lift()
        try:
            self.win.attributes("-topmost", True)
        except tk.TclError:
            pass
        self._apply_chrome()
        _install_overlay_window(self.win, color_key=self.transparent)
        self._blank_cursor()
        self._redraw()
        if self.pointer_locked and self.visible:
            keep_cursor_hidden()

    def hide(self) -> None:
        self.visible = False
        self._aim = (0.0, 0.0)
        self.set_pointer_locked(False)
        self.win.withdraw()
        show_cursor()

    def set_transparent(self, enabled: bool) -> None:
        """Color-key the backing, gaps, and hazard frame. Wedge outlines stay."""
        self.transparent = enabled
        self._apply_chrome()
        _install_overlay_window(self.win, color_key=enabled)
        self._blank_cursor()
        if self.visible:
            self._redraw()

    def _apply_chrome(self) -> None:
        background = TRANSPARENT_KEY if self.transparent else BG
        self.win.configure(bg=background)
        self.canvas.configure(bg=background)
        try:
            self.win.attributes("-transparentcolor", TRANSPARENT_KEY if self.transparent else "")
        except tk.TclError:
            pass

    def set_pointer_locked(self, locked: bool) -> None:
        self.pointer_locked = locked
        self._blank_cursor()
        if locked and self.visible:
            keep_cursor_hidden()

    def _blank_cursor(self) -> None:
        """The overlay never shows an arrow, including inside its rectangle."""
        try:
            self.win.configure(cursor="none")
            self.canvas.configure(cursor="none")
        except tk.TclError:
            pass

    def set_highlight(self, index: int | None) -> None:
        if index is not None and not 0 <= index < len(self.entries):
            index = None
        self.highlight = index
        self._redraw()

    def set_state(self, entries: list[LoadoutEntry], notice: str, bind_label: str) -> None:
        self.entries = list(entries)
        self.notice = notice
        self.bind_label = bind_label
        if self.highlight is not None and self.highlight >= len(self.entries):
            self.highlight = None
        if self.visible:
            self._redraw()

    def selected(self) -> LoadoutEntry | None:
        if self.highlight is None or not 0 <= self.highlight < len(self.entries):
            return None
        return self.entries[self.highlight]

    def pointer(self, x: int, y: int) -> None:
        """Highlight from an on-screen point. Ignored while the cursor is locked."""
        if not self.visible or self.pointer_locked:
            return
        self.apply_offset(x - self.center_screen[0], y - self.center_screen[1])

    def apply_offset(self, dx: float, dy: float) -> None:
        """Highlight from a virtual offset. The deadzone cancels.

        The aim line uses a length clamped to the wheel. The wedge still
        comes from the raw offset.
        """
        if not self.visible:
            return
        self._aim = (float(dx), float(dy))
        index = wedge_index(dx, dy, len(self.entries), self.deadzone)
        if index == self.highlight:
            self._draw_aim()
            return
        self.highlight = index
        self._redraw()

    def _place(self, left: int, top: int) -> None:
        self.center_screen = (left + WHEEL_X, top + WHEEL_Y)
        self.win.geometry(format_geometry(SIZE, SIZE, left, top))

    def _on_left(self, event: tk.Event[tk.Misc]) -> None:
        if not self.demo or self.pointer_locked:
            return
        self.pointer(event.x_root, event.y_root)
        self.on_confirm()

    def _on_middle(self, event: tk.Event[tk.Misc]) -> None:
        # The global listener owns the radial button. A canvas release would
        # re-aim from the parked cursor and cancel a real selection.
        if self.pointer_locked or self.external_bind:
            return
        self.pointer(event.x_root, event.y_root)
        self.on_confirm()

    def _redraw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        if not self.transparent:
            paint_hazard_border(canvas, SIZE, SIZE, band=18, tags=("hazard",))
            canvas.create_text(
                SIZE / 2,
                40,
                text="STRATAGEM WHEEL",
                fill=YELLOW,
                font=(self.title_family, 18, "bold"),
                tags="chrome",
            )
            if self.notice:
                canvas.create_rectangle(36, 58, SIZE - 36, 96, fill=YELLOW, outline="", tags="chrome")
                canvas.create_text(
                    SIZE / 2,
                    77,
                    text=self.notice,
                    fill=BLACK,
                    font=(self.family, 11, "bold"),
                    tags="chrome",
                )
        self._draw_wedges()
        self._draw_center()
        self._draw_aim()
        if not self.transparent:
            canvas.create_text(
                SIZE / 2,
                SIZE - 46,
                text=self._hint(),
                fill=WHITE,
                font=(self.family, 10, "bold"),
                tags="chrome",
            )
            if self.demo:
                canvas.create_text(
                    SIZE / 2,
                    SIZE - 26,
                    text="DEMO · SEQUENCES ARE LOGGED, NOT SENT",
                    fill=MUTED,
                    font=(self.family, 9, "bold"),
                    tags="chrome",
                )

    def _hint(self) -> str:
        if self.demo:
            return f"HOLD {self.bind_label.upper()} OR CLICK A WEDGE · DEADZONE OR ESC CANCELS"
        return f"HOLD {self.bind_label.upper()} · RELEASE TO CALL IN · DEADZONE OR ESC CANCELS"

    def _draw_wedges(self) -> None:
        count = len(self.entries)
        if count == 0:
            return
        selected = self.highlight
        order = [index for index in range(count) if index != selected]
        if selected is not None:
            order.append(selected)
        for index in order:
            self._draw_wedge(index, count, selected=index == selected)

    def _draw_wedge(self, index: int, count: int, *, selected: bool) -> None:
        span = (2 * math.pi) / count
        pad = min(0.04, span * 0.12)
        center = wedge_center_angle(index, count)
        points = _arc_points(WHEEL_X, WHEEL_Y, INNER, OUTER, center - span / 2 + pad, center + span / 2 - pad)
        if self.transparent:
            # Stipple leaves the color key unpainted, so the game shows through the fill.
            self.canvas.create_polygon(
                points,
                fill=YELLOW if selected else "#1A1A1A",
                outline=YELLOW,
                width=2,
                stipple="gray75" if selected else "gray50",
                tags="wedge",
            )
            self._draw_wedge_text(index, count, center, selected=selected)
            return
        fill: str = YELLOW if selected else "#101010"
        outline: str = BLACK if selected else YELLOW
        self.canvas.create_polygon(points, fill=fill, outline=outline, width=2, tags="wedge")
        self._draw_wedge_text(index, count, center, selected=selected)

    def _draw_wedge_text(self, index: int, count: int, angle: float, *, selected: bool) -> None:
        entry = self.entries[index]
        label = _wedge_label(entry.name, count)
        limit = 13 if count >= 9 else 16
        wrapped = _wrap(label, limit)
        name_size = 8 if count >= 9 else 10
        code_size = 9 if count >= 9 else 12
        radius = INNER + (OUTER - INNER) * 0.56
        x = WHEEL_X + math.cos(angle) * radius
        y = WHEEL_Y + math.sin(angle) * radius
        lines = wrapped.count("\n") + 1
        name_color = BLACK if selected else WHITE
        code_color = BLACK if selected else YELLOW
        name_y = y - (code_size + 4) / 2
        self.canvas.create_text(
            x,
            name_y,
            text=wrapped,
            fill=name_color,
            font=(self.family, name_size, "bold"),
            justify="center",
        )
        code_y = name_y + lines * (name_size + 3)
        self.canvas.create_text(
            x,
            code_y,
            text=format_code(entry.code),
            fill=code_color,
            font=(self.family, code_size, "bold"),
            justify="center",
        )

    def _draw_center(self) -> None:
        cx = WHEEL_X
        cy = WHEEL_Y
        radius = self.deadzone
        self.canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill=BLACK,
            outline=YELLOW,
            width=3,
        )
        entry = self.selected()
        if entry is None:
            self.canvas.create_text(cx, cy - 10, text="CANCEL", fill=WHITE, font=(self.title_family, 16, "bold"))
            self.canvas.create_text(cx, cy + 16, text="DEADZONE", fill=YELLOW, font=(self.family, 9, "bold"))
            return
        self.canvas.create_text(
            cx,
            cy - 16,
            text=_wrap(entry.name, 14),
            fill=YELLOW,
            font=(self.family, 11, "bold"),
            justify="center",
            width=radius * 2 - 16,
        )
        self.canvas.create_text(
            cx,
            cy + 22,
            text=format_code(entry.code),
            fill=WHITE,
            font=(self.family, 12, "bold"),
        )

    def _draw_aim(self) -> None:
        """Line from the wheel center. Length is min(offset, wheel radius). No cursor sprite."""
        canvas = self.canvas
        canvas.delete("aim")
        dx, dy = self._aim
        tip_dx, tip_dy = aim_endpoint(dx, dy, OUTER)
        if math.hypot(tip_dx, tip_dy) < 1:
            return
        x0 = WHEEL_X
        y0 = WHEEL_Y
        x1 = WHEEL_X + tip_dx
        y1 = WHEEL_Y + tip_dy
        canvas.create_line(x0, y0, x1, y1, fill=BLACK, width=6, capstyle="round", tags="aim")
        canvas.create_line(x0, y0, x1, y1, fill=YELLOW, width=3, capstyle="round", tags="aim")
        dot = 7
        canvas.create_oval(
            x1 - dot,
            y1 - dot,
            x1 + dot,
            y1 + dot,
            fill=BLACK,
            outline=YELLOW,
            width=2,
            tags="aim",
        )


def _wedge_label(name: str, count: int) -> str:
    short = short_alias(name)
    if count >= 8 and short and len(short) < len(name):
        return short
    return name


def _wrap(text: str, limit: int) -> str:
    words = text.split()
    if not words:
        return text
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if len(trial) <= limit:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return "\n".join(lines[:3])


def _arc_points(
    cx: float,
    cy: float,
    inner: float,
    outer: float,
    start: float,
    end: float,
    steps: int = 10,
) -> list[float]:
    points: list[float] = []
    for index in range(steps + 1):
        angle = start + (end - start) * index / steps
        points.extend((cx + math.cos(angle) * outer, cy + math.sin(angle) * outer))
    for index in range(steps + 1):
        angle = end - (end - start) * index / steps
        points.extend((cx + math.cos(angle) * inner, cy + math.sin(angle) * inner))
    return points


def overlay_ex_style(current: int) -> int:
    """Borderless topmost layered window that does not hit-test or take focus."""
    return int(current) | _OVERLAY_EXSTYLE


def _install_overlay_window(window: tk.Toplevel, *, color_key: bool) -> None:
    """Click-through on Windows. Other platforms keep the Tk frameless window."""
    if sys.platform != "win32":
        return
    window.update_idletasks()
    user32 = ctypes.windll.user32
    hwnd = _top_level_hwnd(user32, int(window.winfo_id()))
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    user32.SetWindowLongW.restype = ctypes.c_long
    style = overlay_ex_style(int(user32.GetWindowLongW(hwnd, -20)))
    user32.SetWindowLongW(hwnd, -20, style)
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    no_move = 0x0001
    no_size = 0x0002
    no_activate = 0x0010
    frame_changed = 0x0020
    user32.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, no_move | no_size | no_activate | frame_changed)
    user32.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.DWORD, wintypes.BYTE, wintypes.DWORD]
    user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
    if color_key:
        user32.SetLayeredWindowAttributes(hwnd, _COLOR_KEY_REF, 255, _LWA_COLORKEY | _LWA_ALPHA)
    else:
        user32.SetLayeredWindowAttributes(hwnd, 0, 255, _LWA_ALPHA)
    _set_blank_class_cursor(user32, hwnd)


def _top_level_hwnd(user32: ctypes.WinDLL, child: int) -> int:
    user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
    user32.GetAncestor.restype = wintypes.HWND
    root = int(user32.GetAncestor(child, 2) or 0)
    if root:
        return root
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND
    parent = int(user32.GetParent(child) or 0)
    return parent or child


_blank_cursor_handle = 0


def _set_blank_class_cursor(user32: ctypes.WinDLL, hwnd: int) -> None:
    global _blank_cursor_handle
    if not _blank_cursor_handle:
        and_mask = (ctypes.c_ubyte * 128)(*([0xFF] * 128))
        xor_mask = (ctypes.c_ubyte * 128)(*([0] * 128))
        user32.CreateCursor.argtypes = [
            wintypes.HINSTANCE,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        user32.CreateCursor.restype = wintypes.HANDLE
        handle = user32.CreateCursor(None, 0, 0, 32, 32, and_mask, xor_mask)
        _blank_cursor_handle = int(handle or 0)
    if not _blank_cursor_handle:
        return
    gcl_hcursor = -12
    if ctypes.sizeof(ctypes.c_void_p) == 8 and hasattr(user32, "SetClassLongPtrW"):
        user32.SetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetClassLongPtrW.restype = ctypes.c_void_p
        user32.SetClassLongPtrW(hwnd, gcl_hcursor, _blank_cursor_handle)
        return
    user32.SetClassLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    user32.SetClassLongW.restype = ctypes.c_ulong
    user32.SetClassLongW(hwnd, gcl_hcursor, _blank_cursor_handle)
