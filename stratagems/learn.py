"""Tag arrow shapes captured from the calibrated region."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from PIL import Image, ImageTk

from stratagems.glyphs import PATCH, GlyphCluster, lut_from_tags
from stratagems.theme import BG, BLACK, DIM, WHITE, YELLOW, pick_family
from stratagems.widgets import yellow_button

_DIRECTIONS = ("up", "down", "left", "right")


class LearnWindow:
    """Show each unique glyph and store the direction the user assigns."""

    def __init__(
        self,
        root: tk.Misc,
        clusters: list[GlyphCluster],
        on_save: Callable[[dict[str, list[str]]], None],
    ) -> None:
        self._clusters = clusters
        self._on_save = on_save
        self._photos: list[ImageTk.PhotoImage] = []
        self._tags = [tk.StringVar(value="") for _cluster in clusters]
        self.family = pick_family(("Segoe UI", "DejaVu Sans", "sans-serif"))
        self.win = tk.Toplevel(root)
        self.win.title("Learn arrow shapes")
        self.win.configure(bg=BG)
        self.win.geometry("760x640")
        self.win.minsize(640, 420)
        self._build()

    def _build(self) -> None:
        tk.Label(
            self.win,
            text="LEARN ARROWS",
            bg=BG,
            fg=YELLOW,
            font=(self.family, 14, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 0))
        tk.Label(
            self.win,
            text=(
                "Each patch is a shape from the calibrated region. "
                "Tag the arrows Up, Down, Left, or Right. Mark everything else Not an arrow."
            ),
            bg=BG,
            fg=DIM,
            wraplength=700,
            justify="left",
            font=(self.family, 9),
        ).pack(anchor="w", padx=16, pady=(4, 8))

        canvas = tk.Canvas(self.win, bg=BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=12)
        scroll = tk.Scrollbar(self.win, orient="vertical", command=canvas.yview)
        scroll.place(relx=1.0, rely=0.12, relheight=0.72, anchor="ne")
        canvas.configure(yscrollcommand=scroll.set)
        body = tk.Frame(canvas, bg=BG)
        window_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def _fit(event: tk.Event[tk.Misc]) -> None:
            canvas.itemconfigure(window_id, width=event.width)
            canvas.configure(scrollregion=canvas.bbox("all"))

        body.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", _fit)

        for index, cluster in enumerate(self._clusters):
            self._row(body, index, cluster)

        actions = tk.Frame(self.win, bg=BG)
        actions.pack(fill="x", padx=16, pady=12)
        yellow_button(actions, "SAVE SAMPLES", self._save, self.family).pack(side="left")
        yellow_button(actions, "CANCEL", self.win.destroy, self.family).pack(side="left", padx=8)

    def _row(self, parent: tk.Misc, index: int, cluster: GlyphCluster) -> None:
        row = tk.Frame(parent, bg=BLACK, highlightthickness=1, highlightbackground=YELLOW)
        row.pack(fill="x", pady=4, padx=4)
        image = Image.frombytes("L", (PATCH, PATCH), cluster.patch).resize((72, 72), Image.Resampling.NEAREST)
        photo = ImageTk.PhotoImage(image)
        self._photos.append(photo)
        tk.Label(row, image=photo, bg=BLACK).pack(side="left", padx=8, pady=8)
        seen = "once" if cluster.count == 1 else f"{cluster.count} times"
        tk.Label(
            row,
            text=f"Shape {index + 1}\nseen {seen}",
            bg=BLACK,
            fg=WHITE,
            justify="left",
            font=(self.family, 9),
        ).pack(side="left", padx=(0, 8))
        choices = tk.Frame(row, bg=BLACK)
        choices.pack(side="left", fill="x", expand=True)
        for label, value in (
            ("UP", "up"),
            ("DOWN", "down"),
            ("LEFT", "left"),
            ("RIGHT", "right"),
            ("NOT AN ARROW", ""),
        ):
            tk.Radiobutton(
                choices,
                text=label,
                value=value,
                variable=self._tags[index],
                bg=BLACK,
                fg=YELLOW,
                selectcolor=BG,
                activebackground=BLACK,
                activeforeground=YELLOW,
                font=(self.family, 9),
                highlightthickness=0,
            ).pack(side="left", padx=4)

    def _save(self) -> None:
        tags = [variable.get() for variable in self._tags]
        if not any(tag in _DIRECTIONS for tag in tags):
            return
        self._on_save(lut_from_tags(self._clusters, tags))
        self.win.destroy()
