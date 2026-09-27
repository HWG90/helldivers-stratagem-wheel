"""Frameless, always-on-top radial wheel."""

from __future__ import annotations

import math
import sys
import tkinter as tk
from collections.abc import Callable

import ctypes

from stratagems.arrows import format_code
from stratagems.catalog import LoadoutEntry
from stratagems.matching import short_alias
from stratagems.radial_math import wedge_center_angle, wedge_index
from stratagems.theme import BG, BLACK, BODY_CANDIDATES, MUTED, TITLE_CANDIDATES, WHITE, YELLOW, pick_family
from stratagems.widgets import paint_hazard_border

SIZE = 800
OUTER = 268
INNER = 102
DEADZONE = 90


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
        self.canvas = tk.Canvas(self.win, width=SIZE, height=SIZE, bg=BG, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_left)
        self.canvas.bind("<ButtonRelease-2>", self._on_middle)
        self.win.bind("<Escape>", lambda _event: self.on_cancel())

    def show(
        self,
        screen_x: int,
        screen_y: int,
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
        self._place(screen_x, screen_y)
        self.visible = True
        self.win.deiconify()
        self.win.lift()
        try:
            self.win.attributes("-topmost", True)
        except tk.TclError:
            pass
        _no_activate(self.win)
        self._redraw()

    def hide(self) -> None:
        self.visible = False
        self.win.withdraw()

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
        if not self.visible:
            return
        dx = x - self.center_screen[0]
        dy = y - self.center_screen[1]
        index = wedge_index(dx, dy, len(self.entries), self.deadzone)
        if index == self.highlight:
            return
        self.highlight = index
        self._redraw()

    def _place(self, screen_x: int, screen_y: int) -> None:
        screen_w = self.win.winfo_screenwidth()
        screen_h = self.win.winfo_screenheight()
        left = int(screen_x - SIZE / 2)
        top = int(screen_y - SIZE / 2)
        left = max(0, min(left, max(0, screen_w - SIZE)))
        top = max(0, min(top, max(0, screen_h - SIZE)))
        self.center_screen = (left + SIZE // 2, top + SIZE // 2)
        self.win.geometry(f"{SIZE}x{SIZE}+{left}+{top}")

    def _on_motion(self, event: tk.Event[tk.Misc]) -> None:
        self.pointer(event.x_root, event.y_root)

    def _on_left(self, event: tk.Event[tk.Misc]) -> None:
        if not self.demo:
            return
        self.pointer(event.x_root, event.y_root)
        self.on_confirm()

    def _on_middle(self, event: tk.Event[tk.Misc]) -> None:
        self.pointer(event.x_root, event.y_root)
        self.on_confirm()

    def _redraw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        paint_hazard_border(canvas, SIZE, SIZE, band=18)
        canvas.create_text(
            SIZE / 2,
            40,
            text="STRATAGEM WHEEL",
            fill=YELLOW,
            font=(self.title_family, 18, "bold"),
        )
        if self.notice:
            canvas.create_rectangle(36, 58, SIZE - 36, 96, fill=YELLOW, outline="")
            canvas.create_text(
                SIZE / 2,
                77,
                text=self.notice,
                fill=BLACK,
                font=(self.family, 11, "bold"),
            )
        self._draw_wedges()
        self._draw_center()
        hint = self._hint()
        canvas.create_text(SIZE / 2, SIZE - 46, text=hint, fill=WHITE, font=(self.family, 10, "bold"))
        if self.demo:
            canvas.create_text(
                SIZE / 2,
                SIZE - 26,
                text="DEMO · SEQUENCES ARE LOGGED, NOT SENT",
                fill=MUTED,
                font=(self.family, 9, "bold"),
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
        points = _arc_points(SIZE / 2, 430, INNER, OUTER, center - span / 2 + pad, center + span / 2 - pad)
        fill: str = YELLOW if selected else "#101010"
        outline: str = BLACK if selected else YELLOW
        self.canvas.create_polygon(points, fill=fill, outline=outline, width=2)
        self._draw_wedge_text(index, count, center, selected=selected)

    def _draw_wedge_text(self, index: int, count: int, angle: float, *, selected: bool) -> None:
        entry = self.entries[index]
        label = _wedge_label(entry.name, count)
        limit = 13 if count >= 9 else 16
        wrapped = _wrap(label, limit)
        name_size = 8 if count >= 9 else 10
        code_size = 9 if count >= 9 else 12
        radius = INNER + (OUTER - INNER) * 0.56
        x = SIZE / 2 + math.cos(angle) * radius
        y = 430 + math.sin(angle) * radius
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
        cx = SIZE / 2
        cy = 430
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


def _no_activate(window: tk.Toplevel) -> None:
    """Keep the overlay from taking focus on Windows so keystrokes reach the game."""
    if sys.platform != "win32":
        return
    window.update_idletasks()
    user32 = ctypes.windll.user32
    hwnd = user32.GetParent(window.winfo_id()) or window.winfo_id()
    style = user32.GetWindowLongW(hwnd, -20)
    no_activate = 0x08000000
    toolwindow = 0x00000080
    topmost = 0x00000008
    user32.SetWindowLongW(hwnd, -20, style | no_activate | toolwindow | topmost)
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
