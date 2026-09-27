"""Helldivers industrial palette."""

from __future__ import annotations

import tkinter.font as tkfont

YELLOW = "#FFE900"
BLACK = "#000000"
WHITE = "#FFFFFF"
BG = "#0C0C0C"
PANEL = "#141414"
MUTED = "#C8C8C8"
DIM = "#8A8A8A"

TITLE_CANDIDATES = ("Arial Black", "Impact", "Liberation Sans", "DejaVu Sans")
BODY_CANDIDATES = ("Liberation Sans", "DejaVu Sans", "Arial")
MONO_CANDIDATES = ("DejaVu Sans Mono", "Liberation Mono", "Consolas", "Courier New")


def pick_family(candidates: tuple[str, ...]) -> str:
    available = set(tkfont.families())
    for name in candidates:
        if name in available:
            return name
    return "TkDefaultFont"
