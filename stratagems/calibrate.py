"""Drag a rectangle on a desktop screenshot to store the OCR region."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from PIL import Image, ImageTk

from stratagems.config import Region
from stratagems.ocr import OcrError, virtual_screen
from stratagems.theme import BG, BLACK, BODY_CANDIDATES, WHITE, YELLOW, pick_family
from stratagems.widgets import body_label, yellow_button

MAX_DISPLAY_W = 1200
MAX_DISPLAY_H = 720


def display_rect_to_screen(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    scale: float,
    origin_x: int,
    origin_y: int,
) -> Region:
    if scale <= 0:
        raise ValueError("scale must be positive")
    left = int(round(min(x0, x1) / scale)) + origin_x
    top = int(round(min(y0, y1) / scale)) + origin_y
    width = max(1, int(round(abs(x1 - x0) / scale)))
    height = max(1, int(round(abs(y1 - y0) / scale)))
    return Region(left, top, width, height)


class CalibrateWindow:
    def __init__(self, root: tk.Tk, on_save: Callable[[Region], None]) -> None:
        self._on_save = on_save
        self.family = pick_family(BODY_CANDIDATES)
        self.scale = 1.0
        self.origin = (0, 0)
        self._start: tuple[int, int] | None = None
        self._end: tuple[int, int] | None = None
        self._rect: int | None = None
        self._photo: ImageTk.PhotoImage | None = None

        self.win = tk.Toplevel(root)
        self.win.title("Calibrate stratagem region")
        self.win.configure(bg=BG)
        self.win.transient(root)
        body_label(
            self.win,
            "Drag a rectangle around the stratagem list. Include the names and the arrow codes on each row.",
            self.family,
            fg=YELLOW,
            size=11,
        ).pack(anchor="w", padx=12, pady=(12, 4))
        self.status = body_label(self.win, "Capturing the desktop…", self.family)
        self.status.pack(anchor="w", padx=12, pady=(0, 8))

        self.canvas = tk.Canvas(self.win, bg=BLACK, highlightthickness=1, highlightbackground=YELLOW, cursor="crosshair")
        self.canvas.pack(padx=12, pady=4)
        actions = tk.Frame(self.win, bg=BG)
        actions.pack(fill="x", padx=12, pady=12)
        self.save_button = yellow_button(actions, "SAVE REGION", self._save, self.family)
        self.save_button.pack(side="left")
        self.save_button.configure(state="disabled")
        yellow_button(actions, "CANCEL", self.win.destroy, self.family).pack(side="left", padx=8)

        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.win.after(50, self._capture)
        self.win.grab_set()

    def _capture(self) -> None:
        try:
            image, origin_x, origin_y = virtual_screen()
        except (OcrError, OSError) as exc:
            self.status.configure(text=f"Could not capture the screen: {exc}")
            return
        self.origin = (origin_x, origin_y)
        self.scale = min(MAX_DISPLAY_W / image.width, MAX_DISPLAY_H / image.height, 1)
        display = image.resize(
            (max(1, int(image.width * self.scale)), max(1, int(image.height * self.scale))),
            Image.Resampling.LANCZOS,
        )
        self._photo = ImageTk.PhotoImage(display)
        self.canvas.configure(width=display.width, height=display.height)
        self.canvas.create_image(0, 0, image=self._photo, anchor="nw")
        self.status.configure(
            text="Drag around the list, then save. The wheel reads this rectangle when it opens."
        )

    def _press(self, event: tk.Event[tk.Misc]) -> None:
        self._start = (event.x, event.y)
        if self._rect is not None:
            self.canvas.delete(self._rect)
        self._rect = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline=YELLOW, width=2
        )

    def _drag(self, event: tk.Event[tk.Misc]) -> None:
        if self._start is None or self._rect is None:
            return
        x0, y0 = self._start
        self.canvas.coords(self._rect, x0, y0, event.x, event.y)

    def _release(self, event: tk.Event[tk.Misc]) -> None:
        if self._start is None:
            return
        x0, y0 = self._start
        if abs(event.x - x0) < 8 or abs(event.y - y0) < 8:
            self.save_button.configure(state="disabled")
            self.status.configure(text="Drag a larger rectangle. The region needs both names and arrows.")
            return
        self._end = (event.x, event.y)
        self.save_button.configure(state="normal")
        region = self._region(event.x, event.y)
        self.status.configure(
            text=f"Region {region.left}, {region.top}  {region.width}×{region.height}. Save to keep it."
        )

    def _region(self, x1: int, y1: int) -> Region:
        assert self._start is not None
        x0, y0 = self._start
        return display_rect_to_screen(
            x0,
            y0,
            x1,
            y1,
            scale=self.scale,
            origin_x=self.origin[0],
            origin_y=self.origin[1],
        )

    def _save(self) -> None:
        if self._start is None or self._end is None:
            return
        x1, y1 = self._end
        self._on_save(self._region(x1, y1))
        self.win.destroy()
