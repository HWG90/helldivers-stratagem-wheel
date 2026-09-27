"""Normal settings window. The radial wheel is a separate overlay."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import ttk

from PIL import Image, ImageTk

from stratagems.arrows import format_code
from stratagems.binds import display_bind
from stratagems.calibrate import CalibrateWindow
from stratagems.catalog import MAX_WHEEL, STRATAGEMS, grouped
from stratagems.config import Config, Region, config_path
from stratagems.hdr import (
    BLACK_MAX,
    BLACK_MIN,
    BLACK_STEP,
    CONTRAST_MAX,
    CONTRAST_MIN,
    CONTRAST_STEP,
    EXPOSURE_MAX,
    EXPOSURE_MIN,
    EXPOSURE_STEP,
    GAMMA_MAX,
    GAMMA_MIN,
    GAMMA_STEP,
    HdrCurve,
    auto_curve,
)
from stratagems.glyphs import arrow_preview
from stratagems.loadout_log import recognition_block_reason
from stratagems.ocr import OcrError, capture_region
from stratagems.sequence import format_plan, plan_input
from stratagems.theme import BG, BLACK, BODY_CANDIDATES, DIM, MONO_CANDIDATES, PANEL, WHITE, YELLOW, pick_family
from stratagems.widgets import body_label, paint_hazard_border, yellow_button

_PREVIEW_W = 720
_PREVIEW_H = 280
_UNCALIBRATED = "No region calibrated. Drag a rectangle around the stratagem list."
_IDLE = "Press Scan or the scan bind to capture this region."


@dataclass(frozen=True)
class SettingsHooks:
    on_changed: Callable[[], None]
    on_rescan: Callable[[], None]
    on_learn: Callable[[], None]
    on_preview: Callable[[], None]
    arm_capture: Callable[[Callable[[str | None], None]], None]


class SettingsWindow:
    def __init__(self, root: tk.Tk, config: Config, hooks: SettingsHooks, *, demo: bool) -> None:
        self.root = root
        self.config = config
        self.hooks = hooks
        self.demo = demo
        self._loading = True
        self.family = pick_family(BODY_CANDIDATES)
        self.mono = pick_family(MONO_CANDIDATES)
        self._bind_labels: dict[str, tk.Label] = {}
        self._checks: dict[str, tk.BooleanVar] = {}
        self._filter = tk.StringVar()
        self.status = tk.StringVar(value="Ready.")
        self._crop: Image.Image | None = None
        self._preview_photo: ImageTk.PhotoImage | None = None
        self._body_canvas: tk.Canvas | None = None

        self._build()
        self._loading = False

    def set_status(self, text: str) -> None:
        self.status.set(text)

    def append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text.rstrip() + "\n\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _build(self) -> None:
        header = tk.Canvas(self.root, height=72, bg=BLACK, highlightthickness=0)
        header.pack(fill="x")
        subtitle = (
            "DEMO — KEYS ARE LOGGED, NOT SENT"
            if self.demo
            else "LIVE — CONFIRMED WEDGES TYPE ORDINARY KEYPRESSES"
        )

        def paint_header(_event: object = None) -> None:
            width = max(header.winfo_width(), 640)
            header.delete("all")
            paint_hazard_border(header, width, 72, band=8)
            header.create_text(width / 2, 26, text="STRATAGEM TERMINAL", fill=YELLOW, font=(self.family, 18, "bold"))
            header.create_text(width / 2, 50, text=subtitle, fill=WHITE, font=(self.family, 9, "bold"))

        header.bind("<Configure>", paint_header)
        self.root.after_idle(paint_header)

        body = self._scrolling_body()

        self._build_binds(body)
        self._build_wheel(body)
        self._build_input(body)
        self._build_calibration(body)
        self._build_hdr(body)
        self._build_loadout(body)
        self._build_dry_run(body)

        tk.Label(self.root, textvariable=self.status, bg=BG, fg=YELLOW, anchor="w", font=(self.family, 9)).pack(
            fill="x", padx=16
        )
        footer = (
            f"Config {config_path()}    ·    Ordinary keypresses only. "
            "Helldivers 2 anti-cheat may still flag macros."
        )
        tk.Label(self.root, text=footer, bg=BG, fg=DIM, anchor="w", font=(self.family, 8), wraplength=900, justify="left").pack(
            fill="x", padx=16, pady=(0, 10)
        )

    def _scrolling_body(self) -> tk.Frame:
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=16, pady=8)
        canvas = tk.Canvas(shell, bg=BG, highlightthickness=0, borderwidth=0)
        bar = tk.Scrollbar(shell, orient="vertical", command=canvas.yview, bg=PANEL, troughcolor=BLACK)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def fit_inner(event: tk.Event[tk.Misc]) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        def fit_scroll(_event: tk.Event[tk.Misc]) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", fit_inner)
        inner.bind("<Configure>", fit_scroll)
        self._body_canvas = canvas
        self.root.bind_all("<Button-4>", self._on_wheel, add="+")
        self.root.bind_all("<Button-5>", self._on_wheel, add="+")
        self.root.bind_all("<MouseWheel>", self._on_wheel, add="+")
        return inner

    def _on_wheel(self, event: tk.Event[tk.Misc]) -> None:
        delta = getattr(event, "delta", 0)
        number = getattr(event, "num", 0)
        step = -3 if number == 4 or delta > 0 else 3
        self._wheel_target(event).yview_scroll(step, "units")

    def _wheel_target(self, event: tk.Event[tk.Misc]) -> tk.Canvas:
        checklist = getattr(self, "check_canvas", None)
        widget = self.root.winfo_containing(int(event.x_root), int(event.y_root))
        while widget is not None and checklist is not None:
            if widget == checklist:
                return checklist
            parent = getattr(widget, "master", None)
            widget = parent if isinstance(parent, tk.Misc) else None
        if self._body_canvas is not None:
            return self._body_canvas
        if checklist is None:
            raise RuntimeError("The settings window has no scrollable surface yet.")
        return checklist

    def _section(self, parent: tk.Misc, title: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="x", pady=(8, 2))
        tk.Label(frame, text=title, bg=BG, fg=YELLOW, font=(self.family, 11, "bold")).pack(anchor="w")
        return frame

    def _build_binds(self, parent: tk.Misc) -> None:
        frame = self._section(parent, "BINDS")
        self._bind_row(frame, "Radial trigger", "radial_bind")
        self._bind_row(frame, "Rescan", "rescan_bind")
        self._bind_row(frame, "Learn arrows", "learn_bind")
        self._bind_row(frame, "Stratagem modifier", "modifier")
        body_label(
            frame,
            "Hold the radial bind to open the wheel at the center of the monitor under the cursor. "
            "The wheel uses the last scan. It does not capture the screen. "
            "Mouse5, or LEARN, tags arrow shapes from the list. Mouse4, or SCAN, matches those saved shapes once. "
            "The preview does not refresh on a timer. "
            "The OS cursor hides while you hold the wheel. A line from the wheel center to a dot shows the aim. "
            "Release on a wedge to type that code. Release in the center, or press Escape, to cancel. "
            "Rebind accepts mouse buttons and keys.",
            self.family,
            fg=DIM,
            size=8,
        ).pack(anchor="w", pady=(4, 0))

    def _build_wheel(self, parent: tk.Misc) -> None:
        frame = self._section(parent, "WHEEL")
        self.transparent_var = tk.BooleanVar(value=self.config.transparent_wheel)
        tk.Checkbutton(
            frame,
            text="Transparent wheel",
            variable=self.transparent_var,
            command=self._on_transparent,
            bg=BG,
            fg=WHITE,
            selectcolor=YELLOW,
            activebackground=BG,
            activeforeground=YELLOW,
            font=(self.family, 10),
            highlightthickness=0,
            anchor="w",
        ).pack(anchor="w")
        body_label(
            frame,
            "Off by default. When on, each wedge keeps its yellow outline and the fill is see-through. "
            "The backing, the gaps, and the hazard frame are a transparent color key. "
            "Labels and the center readout stay readable.",
            self.family,
            fg=DIM,
            size=8,
        ).pack(anchor="w", pady=(4, 0))

    def _on_transparent(self) -> None:
        if self._loading:
            return
        self.config.transparent_wheel = bool(self.transparent_var.get())
        self.hooks.on_changed()

    def _bind_row(self, parent: tk.Misc, label: str, field: str) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, width=24, anchor="w", bg=BG, fg=WHITE, font=(self.family, 10)).pack(side="left")
        value = tk.Label(
            row,
            text=display_bind(str(getattr(self.config, field))),
            width=22,
            anchor="w",
            bg=PANEL,
            fg=YELLOW,
            font=(self.mono, 10),
            padx=8,
        )
        value.pack(side="left", padx=8)
        yellow_button(row, "REBIND", lambda field=field: self._begin_rebind(field), self.family).pack(side="left")
        self._bind_labels[field] = value

    def _begin_rebind(self, field: str) -> None:
        self.set_status("Press a mouse button or a key. Escape cancels.")
        self.hooks.arm_capture(lambda name, field=field: self._apply_bind(field, name))

    def _apply_bind(self, field: str, name: str | None) -> None:
        if not name or name == "esc":
            self.set_status("Rebind cancelled.")
            return
        setattr(self.config, field, name)
        self._bind_labels[field].configure(text=display_bind(name))
        self.hooks.on_changed()
        self.set_status(f"{field.replace('_', ' ').title()} is {display_bind(name)}.")

    def _build_input(self, parent: tk.Misc) -> None:
        frame = self._section(parent, "INPUT")
        style_row = tk.Frame(frame, bg=BG)
        style_row.pack(fill="x", pady=2)
        tk.Label(style_row, text="Direction keys", bg=BG, fg=WHITE, font=(self.family, 10)).pack(side="left")
        self.style_var = tk.StringVar(value=self.config.direction_style)
        for value, label in (("arrows", "Arrow keys"), ("wasd", "WASD")):
            tk.Radiobutton(
                style_row,
                text=label,
                value=value,
                variable=self.style_var,
                command=self._on_style,
                bg=BG,
                fg=WHITE,
                selectcolor=BLACK,
                activebackground=BG,
                activeforeground=YELLOW,
                font=(self.family, 10),
                highlightthickness=0,
            ).pack(side="left", padx=8)

        grid = tk.Frame(frame, bg=BG)
        grid.pack(fill="x", pady=4)
        self.start_var = tk.StringVar(value=str(self.config.start_delay_ms))
        self.gap_var = tk.StringVar(value=str(self.config.gap_ms))
        self.tail_var = tk.StringVar(value=str(self.config.tail_ms))
        self.tap_var = tk.StringVar(value=str(self.config.tap_ms))
        fields = (
            (self.start_var, "Delay before first direction (ms)", "80"),
            (self.gap_var, "Gap between directions (ms)", "50"),
            (self.tail_var, "Tail before modifier release (ms)", "40"),
            (self.tap_var, "Direction key hold (ms)", "20"),
        )
        for column, (variable, label, _default) in enumerate(fields):
            cell = tk.Frame(grid, bg=BG)
            cell.grid(row=0, column=column, padx=(0, 12), sticky="w")
            tk.Label(cell, text=label, bg=BG, fg=WHITE, font=(self.family, 8)).pack(anchor="w")
            spin = tk.Spinbox(
                cell,
                from_=0,
                to=2000,
                textvariable=variable,
                width=6,
                bg=PANEL,
                fg=YELLOW,
                buttonbackground=YELLOW,
                insertbackground=YELLOW,
                relief="flat",
                font=(self.mono, 12),
                justify="right",
            )
            spin.pack(anchor="w")
            variable.trace_add("write", self._on_numbers)
        body_label(
            frame,
            "Defaults are 80 ms before the first arrow, 50 ms between arrows, and 40 ms of tail "
            "before Left Control is released. Each direction is held for 20 ms. That is a human-speed "
            "cadence a game sample can register.",
            self.family,
            fg=DIM,
            size=8,
        ).pack(anchor="w", pady=(4, 0))

    def _on_style(self) -> None:
        if self._loading:
            return
        self.config.direction_style = "wasd" if self.style_var.get() == "wasd" else "arrows"
        self.hooks.on_changed()

    def _on_numbers(self, *_args: object) -> None:
        if self._loading:
            return
        self.config.start_delay_ms = _ms(self.start_var.get(), self.config.start_delay_ms)
        self.config.gap_ms = _ms(self.gap_var.get(), self.config.gap_ms)
        self.config.tail_ms = _ms(self.tail_var.get(), self.config.tail_ms)
        self.config.tap_ms = _ms(self.tap_var.get(), self.config.tap_ms)
        self.hooks.on_changed()

    def _build_calibration(self, parent: tk.Misc) -> None:
        frame = self._section(parent, "SCREEN REGION")
        self.region_label = body_label(frame, "", self.family, size=10)
        self.region_label.pack(anchor="w", pady=2)
        self._refresh_region()
        row = tk.Frame(frame, bg=BG)
        row.pack(anchor="w", pady=4)
        yellow_button(row, "CALIBRATE", self._calibrate, self.family).pack(side="left")
        yellow_button(row, "CLEAR", self._clear_region, self.family).pack(side="left", padx=8)
        yellow_button(row, "LEARN", self.hooks.on_learn, self.family).pack(side="left")
        yellow_button(row, "SCAN", self.hooks.on_rescan, self.family).pack(side="left", padx=8)

    def _refresh_region(self) -> None:
        region = self.config.region
        if region is None:
            text = "Not calibrated. The wheel uses the built-in sample loadout until you drag a rectangle."
        else:
            text = f"Saved region  {region.left}, {region.top}   {region.width} × {region.height}"
        self.region_label.configure(text=text)

    def _calibrate(self) -> None:
        CalibrateWindow(self.root, self._on_region)

    def _on_region(self, region: Region) -> None:
        self.config.region = region
        self._refresh_region()
        self.hooks.on_changed()
        self.set_status(f"Saved region {region.left}, {region.top} {region.width}×{region.height}.")
        self._crop = None
        self._show_preview_message(_IDLE)

    def _clear_region(self) -> None:
        self.config.region = None
        self._refresh_region()
        self.hooks.on_changed()
        self.set_status("Region cleared. The wheel is back on the sample loadout.")
        self._show_uncalibrated()

    def _build_hdr(self, parent: tk.Misc) -> None:
        frame = self._section(parent, "HDR")
        self.hdr_var = tk.BooleanVar(value=self.config.hdr)
        tk.Checkbutton(
            frame,
            text="Adjust captures before reading (Windows HDR)",
            variable=self.hdr_var,
            command=self._on_hdr_toggle,
            bg=BG,
            fg=WHITE,
            selectcolor=YELLOW,
            activebackground=BG,
            activeforeground=YELLOW,
            font=(self.family, 10),
            highlightthickness=0,
            anchor="w",
        ).pack(anchor="w")
        help_text = body_label(
            frame,
            "HDR screenshots often come back flat, dark, or blown out. "
            "The preview shows each segmented arrow and the direction the matcher chose. "
            "It updates when you press the scan bind, click Scan or Auto, or release a slider. "
            "It does not replace the saved mission loadout. "
            "Auto sets the curve from one crop. Nudge the sliders if a glyph is still soft.",
            self.family,
            fg=DIM,
            size=8,
        )
        help_text.configure(wraplength=860)
        help_text.pack(anchor="w", pady=(2, 4))

        self.exposure_var = tk.DoubleVar(value=self.config.hdr_exposure)
        self.gamma_var = tk.DoubleVar(value=self.config.hdr_gamma)
        self.contrast_var = tk.DoubleVar(value=self.config.hdr_contrast)
        self.black_var = tk.DoubleVar(value=self.config.hdr_black_level)
        self.exposure_text = tk.StringVar()
        self.gamma_text = tk.StringVar()
        self.contrast_text = tk.StringVar()
        self.black_text = tk.StringVar()
        grid = tk.Frame(frame, bg=BG)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        self._hdr_slider(
            grid, "Exposure (stops)", self.exposure_var, self.exposure_text,
            low=EXPOSURE_MIN, high=EXPOSURE_MAX, step=EXPOSURE_STEP, row=0, column=0,
        )
        self._hdr_slider(
            grid, "Gamma  ·  lower lifts midtones", self.gamma_var, self.gamma_text,
            low=GAMMA_MIN, high=GAMMA_MAX, step=GAMMA_STEP, row=0, column=1,
        )
        self._hdr_slider(
            grid, "Contrast", self.contrast_var, self.contrast_text,
            low=CONTRAST_MIN, high=CONTRAST_MAX, step=CONTRAST_STEP, row=1, column=0,
        )
        self._hdr_slider(
            grid, "Black level", self.black_var, self.black_text,
            low=BLACK_MIN, high=BLACK_MAX, step=BLACK_STEP, row=1, column=1,
        )
        self._sync_hdr_labels()

        row = tk.Frame(frame, bg=BG)
        row.pack(anchor="w", pady=4)
        yellow_button(row, "AUTO", self._auto_hdr, self.family).pack(side="left")
        self.hdr_note = tk.StringVar()
        self._refresh_hdr_note()
        tk.Label(
            frame,
            textvariable=self.hdr_note,
            bg=BG,
            fg=YELLOW,
            anchor="w",
            justify="left",
            font=(self.family, 8),
        ).pack(anchor="w")

        previews = tk.Frame(frame, bg=BG)
        previews.pack(fill="x", pady=(6, 0))
        self.preview_view = self._preview_pane(previews, "ARROW MATCH")
        self.hdr_ocr = tk.StringVar(value=_UNCALIBRATED)
        if self.config.region is None:
            self._show_uncalibrated()
        else:
            self._show_preview_message(_IDLE)
        ocr = tk.Label(
            frame,
            textvariable=self.hdr_ocr,
            bg=BLACK,
            fg=YELLOW,
            anchor="w",
            justify="left",
            font=(self.mono, 9),
            wraplength=860,
            padx=8,
            pady=6,
            highlightthickness=1,
            highlightbackground=YELLOW,
        )
        ocr.pack(fill="x", pady=(6, 0))

    def _preview_pane(self, parent: tk.Misc, caption: str) -> tk.Label:
        column = tk.Frame(parent, bg=BG)
        column.pack(fill="x")
        tk.Label(column, text=caption, bg=BG, fg=DIM, font=(self.family, 8, "bold")).pack(anchor="w")
        view = tk.Label(
            column,
            text=_UNCALIBRATED,
            bg=BLACK,
            fg=YELLOW,
            font=(self.mono, 10),
            wraplength=680,
            justify="left",
            anchor="nw",
            width=52,
            height=6,
            padx=8,
            pady=8,
            highlightthickness=1,
            highlightbackground=YELLOW,
        )
        view.pack(anchor="w", fill="x")
        return view

    def _hdr_slider(
        self,
        parent: tk.Misc,
        label: str,
        variable: tk.DoubleVar,
        value_var: tk.StringVar,
        *,
        low: float,
        high: float,
        step: float,
        row: int,
        column: int,
    ) -> None:
        cell = tk.Frame(parent, bg=BG)
        cell.grid(row=row, column=column, sticky="ew", padx=(0, 12), pady=2)
        header = tk.Frame(cell, bg=BG)
        header.pack(fill="x")
        tk.Label(header, text=label, bg=BG, fg=WHITE, font=(self.family, 9)).pack(side="left")
        tk.Label(header, textvariable=value_var, bg=BG, fg=YELLOW, font=(self.mono, 9)).pack(side="right")
        scale = tk.Scale(
            cell,
            from_=low,
            to=high,
            resolution=step,
            orient="horizontal",
            variable=variable,
            command=self._on_hdr_slider,
            bg=BG,
            fg=YELLOW,
            troughcolor="#2A2A2A",
            activebackground=YELLOW,
            highlightthickness=0,
            sliderrelief="flat",
            bd=0,
            showvalue=False,
            length=260,
        )
        scale.pack(fill="x")
        scale.bind("<ButtonRelease-1>", self._finish_hdr_slider)
        scale.bind("<KeyRelease>", self._finish_hdr_slider)

    def _sync_hdr_labels(self) -> None:
        self.exposure_text.set(f"{float(self.exposure_var.get()):+.2f} st")
        self.gamma_text.set(f"{float(self.gamma_var.get()):.2f}")
        self.contrast_text.set(f"{float(self.contrast_var.get()):.2f}")
        self.black_text.set(f"{float(self.black_var.get()):.2f}")

    def _refresh_hdr_note(self) -> None:
        if bool(self.hdr_var.get()):
            text = "HDR is on. Arrows are segmented after this curve. The preview does not scan the mission."
        else:
            text = "HDR is off. Arrows are segmented on the unadjusted crop. The preview does not scan the mission."
        self.hdr_note.set(text)

    def _current_curve(self) -> HdrCurve:
        return HdrCurve(
            exposure_stops=float(self.exposure_var.get()),
            gamma=float(self.gamma_var.get()),
            contrast=float(self.contrast_var.get()),
            black_level=float(self.black_var.get()),
        ).clamped()

    def _push_hdr(self) -> None:
        curve = self._current_curve()
        self.config.hdr = bool(self.hdr_var.get())
        self.config.hdr_exposure = round(curve.exposure_stops, 4)
        self.config.hdr_gamma = round(curve.gamma, 4)
        self.config.hdr_contrast = round(curve.contrast, 4)
        self.config.hdr_black_level = round(curve.black_level, 4)
        self._sync_hdr_labels()
        self._refresh_hdr_note()

    def show_capture(self, image: Image.Image) -> None:
        """Show one captured crop. This does not change the mission loadout."""
        if self.config.region is None:
            self._show_uncalibrated()
            return
        self._crop = image
        self._refresh_preview()

    def _on_hdr_toggle(self) -> None:
        if self._loading:
            return
        self._push_hdr()
        if self._crop is not None:
            self._refresh_preview()
        self.hooks.on_changed()

    def _on_hdr_slider(self, _value: str) -> None:
        if self._loading:
            return
        self._sync_hdr_labels()

    def _finish_hdr_slider(self, _event: object = None) -> None:
        if self._loading:
            return
        self._push_hdr()
        if self.config.region is None:
            self._show_uncalibrated()
        elif self._crop is None:
            self._grab_crop_now()
            if self._crop is not None:
                self._refresh_preview()
        else:
            self._refresh_preview()
        self.hooks.on_changed()

    def _auto_hdr(self) -> None:
        if self.config.region is None:
            self._show_uncalibrated()
            self.set_status("Calibrate the stratagem list before using Auto.")
            return
        self._grab_crop_now()
        if self._crop is None:
            return
        curve = auto_curve(self._crop)
        self._loading = True
        try:
            self.hdr_var.set(True)
            self.exposure_var.set(curve.exposure_stops)
            self.gamma_var.set(curve.gamma)
            self.contrast_var.set(curve.contrast)
            self.black_var.set(curve.black_level)
        finally:
            self._loading = False
        self._push_hdr()
        self._refresh_preview()
        self.hooks.on_changed()
        self.set_status("HDR curve set from the crop histogram. Nudge the sliders if a glyph is still soft.")

    def _grab_crop_now(self) -> None:
        region = self.config.region
        if region is None:
            self._show_uncalibrated()
            return
        try:
            self._crop = capture_region(region.left, region.top, region.width, region.height)
        except (OcrError, OSError) as exc:
            self._crop = None
            self._show_preview_message(str(exc))
            self.set_status(str(exc))

    def _show_uncalibrated(self) -> None:
        self._crop = None
        self._show_preview_message(_UNCALIBRATED)

    def _show_preview_message(self, text: str) -> None:
        self._preview_photo = None
        self.preview_view.configure(image="", text=text, width=52, height=6)
        self.hdr_ocr.set(text)

    def _refresh_preview(self) -> None:
        reason = recognition_block_reason(self.config.ocr_fallback, self.config.manual_override)
        if reason:
            self._show_preview_message(reason)
            return
        if self.config.region is None:
            self._show_uncalibrated()
            return
        if self._crop is None:
            self._show_preview_message(_IDLE)
            return
        bitmap, summary = arrow_preview(
            self._crop,
            hdr=bool(self.hdr_var.get()),
            curve=self._current_curve(),
            glyph_lut=self.config.glyph_lut,
        )
        self._preview_photo = _thumb(bitmap)
        self.preview_view.configure(image=self._preview_photo, text="", width=0, height=0)
        self.hdr_ocr.set(summary)

    def _build_loadout(self, parent: tk.Misc) -> None:
        frame = self._section(parent, "LOADOUT SOURCE")
        body_label(frame, "Live log updates are the default. Recognition runs only when enabled below and no log is active.",
                   self.family, fg=DIM, size=8).pack(anchor="w")
        self.ocr_fallback_var = tk.BooleanVar(value=self.config.ocr_fallback)
        tk.Checkbutton(frame, text="Enable OCR / shape recognition as a fallback",
                       variable=self.ocr_fallback_var, command=self._on_ocr_fallback,
                       bg=BG, fg=WHITE, selectcolor=YELLOW, activebackground=BG,
                       activeforeground=YELLOW, font=(self.family, 10), highlightthickness=0,
                       anchor="w").pack(anchor="w")
        self.manual_var = tk.BooleanVar(value=self.config.manual_override)
        tk.Checkbutton(
            frame,
            text="Manual override — pin stratagems and skip the scan",
            variable=self.manual_var,
            command=self._on_manual,
            bg=BG,
            fg=WHITE,
            selectcolor=YELLOW,
            activebackground=BG,
            activeforeground=YELLOW,
            font=(self.family, 10),
            highlightthickness=0,
            anchor="w",
        ).pack(anchor="w")
        filter_row = tk.Frame(frame, bg=BG)
        filter_row.pack(fill="x", pady=2)
        tk.Label(filter_row, text="Filter", bg=BG, fg=WHITE, font=(self.family, 9)).pack(side="left")
        entry = tk.Entry(
            filter_row,
            textvariable=self._filter,
            bg=PANEL,
            fg=YELLOW,
            insertbackground=YELLOW,
            relief="flat",
            font=(self.family, 10),
        )
        entry.pack(side="left", fill="x", expand=True, padx=8)
        self._filter.trace_add("write", lambda *_args: self._rebuild_checks())
        self.pin_count = tk.StringVar()
        tk.Label(frame, textvariable=self.pin_count, bg=BG, fg=DIM, font=(self.family, 8)).pack(anchor="w")

        holder = tk.Frame(frame, bg=BG)
        holder.pack(fill="x", pady=2)
        self.check_canvas = tk.Canvas(
            holder, bg=BG, height=168, width=800, highlightthickness=1, highlightbackground=YELLOW
        )
        scroll = tk.Scrollbar(holder, command=self.check_canvas.yview, bg=PANEL, troughcolor=BLACK)
        self.check_frame = tk.Frame(self.check_canvas, bg=BG)
        self.check_frame.bind("<Configure>", lambda _event: self.check_canvas.configure(scrollregion=self.check_canvas.bbox("all")))
        self._check_window = self.check_canvas.create_window((0, 0), window=self.check_frame, anchor="nw", width=800)
        self.check_canvas.bind("<Configure>", self._size_checks, add="+")
        self.check_canvas.configure(yscrollcommand=scroll.set)
        self.check_canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._rebuild_checks()

    def _size_checks(self, event: tk.Event[tk.Misc]) -> None:
        self.check_canvas.itemconfigure(self._check_window, width=event.width)

    def _on_manual(self) -> None:
        if self._loading:
            return
        self.config.manual_override = bool(self.manual_var.get())
        self.hooks.on_changed()

    def _on_ocr_fallback(self) -> None:
        if self._loading:
            return
        self.config.ocr_fallback = bool(self.ocr_fallback_var.get())
        self._refresh_preview()
        self.hooks.on_changed()

    def _rebuild_checks(self) -> None:
        for child in self.check_frame.winfo_children():
            child.destroy()
        self._checks.clear()
        query = self._filter.get().casefold().strip()
        for kind, items in grouped():
            visible = [item for item in items if not query or query in item.name.casefold() or query in kind.casefold()]
            if not visible:
                continue
            tk.Label(self.check_frame, text=kind.upper(), bg=BG, fg=YELLOW, font=(self.family, 9, "bold")).pack(anchor="w", pady=(6, 0))
            for item in visible:
                var = tk.BooleanVar(value=item.name in self.config.pinned)
                self._checks[item.name] = var
                tk.Checkbutton(
                    self.check_frame,
                    text=f"{item.name}    {format_code(item.code)}",
                    variable=var,
                    command=lambda name=item.name: self._toggle_pin(name),
                    bg=BG,
                    fg=WHITE,
                    selectcolor=YELLOW,
                    activebackground=BG,
                    activeforeground=YELLOW,
                    font=(self.family, 9),
                    highlightthickness=0,
                    anchor="w",
                ).pack(anchor="w")
        shown = len(self.config.pinned)
        extra = f" · the wheel keeps the first {MAX_WHEEL}" if shown > MAX_WHEEL else ""
        self.pin_count.set(f"Pinned {shown}{extra}")

    def _toggle_pin(self, name: str) -> None:
        selected = self._checks[name].get()
        pins = [pin for pin in self.config.pinned if pin != name]
        if selected:
            pins.append(name)
        self.config.pinned = pins
        shown = len(pins)
        extra = f" · the wheel keeps the first {MAX_WHEEL}" if shown > MAX_WHEEL else ""
        self.pin_count.set(f"Pinned {shown}{extra}")
        self.hooks.on_changed()

    def _build_dry_run(self, parent: tk.Misc) -> None:
        frame = self._section(parent, "DRY RUN")
        row = tk.Frame(frame, bg=BG)
        row.pack(fill="x", pady=2)
        names = [item.name for item in STRATAGEMS]
        self.pick = ttk.Combobox(row, values=names, state="readonly", width=42, font=(self.family, 10))
        default = "Eagle Airstrike" if "Eagle Airstrike" in names else names[0]
        self.pick.set(default)
        self.pick.pack(side="left")
        yellow_button(row, "SHOW KEY SEQUENCE", self._show_sequence, self.family).pack(side="left", padx=8)
        yellow_button(row, "PREVIEW WHEEL", self.hooks.on_preview, self.family).pack(side="left")
        self.log = tk.Text(
            frame,
            height=8,
            bg=BLACK,
            fg=YELLOW,
            insertbackground=YELLOW,
            relief="flat",
            font=(self.mono, 10),
            wrap="word",
            highlightthickness=1,
            highlightbackground=YELLOW,
        )
        self.log.pack(fill="x", pady=(6, 0))
        self.append_log(
            "Pick a stratagem and press Show key sequence.\n"
            "Nothing is typed. Confirming a wedge in demo mode writes the same sequence here."
        )

    def _show_sequence(self) -> None:
        name = self.pick.get().strip()
        matches = [item for item in STRATAGEMS if item.name == name]
        if not matches:
            self.set_status("Pick a stratagem first.")
            return
        stratagem = matches[0]
        self._on_numbers()
        steps = plan_input(
            stratagem.code,
            modifier=self.config.modifier,
            style=self.config.direction_style,
            start_delay_ms=self.config.start_delay_ms,
            gap_ms=self.config.gap_ms,
            tail_ms=self.config.tail_ms,
            tap_ms=self.config.tap_ms,
        )
        self.append_log(format_plan(steps, name=stratagem.name, code=stratagem.code))
        self.set_status(f"Dry run for {stratagem.name}. No keys were sent.")


def _ms(text: str, fallback: int) -> int:
    try:
        value = int(text)
    except ValueError:
        return fallback
    return max(0, min(2000, value))


def _thumb(image: Image.Image) -> ImageTk.PhotoImage:
    scale = min(_PREVIEW_W / max(image.width, 1), _PREVIEW_H / max(image.height, 1))
    if scale > 2:
        scale = 2
    width = max(1, int(round(image.width * scale)))
    height = max(1, int(round(image.height * scale)))
    if (width, height) != image.size:
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image)

