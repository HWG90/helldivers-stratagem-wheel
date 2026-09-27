"""Shared drawing helpers for the terminal and the wheel."""

from __future__ import annotations

import tkinter as tk

from stratagems.theme import BG, BLACK, WHITE, YELLOW


def paint_hazard_border(canvas: tk.Canvas, width: int, height: int, band: int = 16) -> None:
    canvas.create_rectangle(0, 0, width, height, fill=YELLOW, outline="")
    stripe = max(8, band)
    x = -height
    while x < width + height:
        canvas.create_polygon(
            x,
            0,
            x + stripe,
            0,
            x + stripe - height,
            height,
            x - height,
            height,
            fill=BLACK,
            outline="",
        )
        x += stripe * 2
    inset = band
    canvas.create_rectangle(
        inset,
        inset,
        width - inset,
        height - inset,
        fill=BG,
        outline=YELLOW,
        width=2,
    )


def yellow_button(parent: tk.Misc, text: str, command: object, family: str) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=YELLOW,
        fg=BLACK,
        activebackground="#FFF35A",
        activeforeground=BLACK,
        relief="flat",
        font=(family, 10, "bold"),
        padx=12,
        pady=4,
        cursor="hand2",
        highlightthickness=0,
    )


def body_label(parent: tk.Misc, text: str, family: str, *, fg: str = WHITE, size: int = 10) -> tk.Label:
    return tk.Label(parent, text=text, bg=BG, fg=fg, font=(family, size), anchor="w", justify="left")
