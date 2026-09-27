"""Normal settings window. The radial wheel is a separate overlay."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import ttk

from stratagems.arrows import format_code
from stratagems.binds import display_bind
from stratagems.calibrate import CalibrateWindow
from stratagems.catalog import MAX_WHEEL, STRATAGEMS, grouped
from stratagems.config import Config, Region, config_path
from stratagems.sequence import format_plan, plan_input
from stratagems.theme import BG, BLACK, BODY_CANDIDATES, DIM, MONO_CANDIDATES, PANEL, WHITE, YELLOW, pick_family
from stratagems.widgets import body_label, paint_hazard_border, yellow_button


@dataclass(frozen=True)
class SettingsHooks:
    on_changed: Callable[[], None]
    on_rescan: Callable[[], None]
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

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=8)

        self._build_binds(body)
        self._build_input(body)
        self._build_calibration(body)
        self._build_loadout(body)
        self._build_dry_run(body)

        tk.Label(self.root, textvariable=self.status, bg=BG, fg=YELLOW, anchor="w", font=(self.family, 9)).pack(
            fill="x", padx=16
        )
        footer = (
            f"Config {config_path()}    ·    Ordinary keypresses only. "
            "Helldivers 2 anti-cheat may still flag macros."
        )
        tk.Label(self.root, text=footer, bg=BG, fg=DIM, anchor="w", font=(self.family, 8), wraplength=820, justify="left").pack(
            fill="x", padx=16, pady=(0, 10)
        )

    def _section(self, parent: tk.Misc, title: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="x", pady=(8, 2))
        tk.Label(frame, text=title, bg=BG, fg=YELLOW, font=(self.family, 11, "bold")).pack(anchor="w")
        return frame

    def _build_binds(self, parent: tk.Misc) -> None:
        frame = self._section(parent, "BINDS")
        self._bind_row(frame, "Radial trigger", "radial_bind")
        self._bind_row(frame, "Rescan", "rescan_bind")
        self._bind_row(frame, "Stratagem modifier", "modifier")
        body_label(
            frame,
            "Hold the radial bind to open the wheel at the cursor. Release on a wedge to type that code. "
            "Release in the center, or press Escape, to cancel. Rebind accepts mouse buttons and keys.",
            self.family,
            fg=DIM,
            size=8,
        ).pack(anchor="w", pady=(4, 0))

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

        self.auto_var = tk.BooleanVar(value=self.config.auto_scan)
        tk.Checkbutton(
            frame,
            text="Auto-scan the calibrated region when the wheel opens",
            variable=self.auto_var,
            command=self._on_auto,
            bg=BG,
            fg=WHITE,
            selectcolor=YELLOW,
            activebackground=BG,
            activeforeground=YELLOW,
            font=(self.family, 10),
            highlightthickness=0,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

    def _on_style(self) -> None:
        if self._loading:
            return
        self.config.direction_style = "wasd" if self.style_var.get() == "wasd" else "arrows"
        self.hooks.on_changed()

    def _on_auto(self) -> None:
        if self._loading:
            return
        self.config.auto_scan = bool(self.auto_var.get())
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
        yellow_button(row, "RESCAN NOW", self.hooks.on_rescan, self.family).pack(side="left")

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

    def _clear_region(self) -> None:
        self.config.region = None
        self._refresh_region()
        self.hooks.on_changed()
        self.set_status("Region cleared. The wheel is back on the sample loadout.")

    def _build_loadout(self, parent: tk.Misc) -> None:
        frame = self._section(parent, "MANUAL LOADOUT")
        self.manual_var = tk.BooleanVar(value=self.config.manual_override)
        tk.Checkbutton(
            frame,
            text="Manual override — pin stratagems and skip OCR",
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
        self.check_canvas.bind("<Enter>", lambda _event: self._bind_wheel(True))
        self.check_canvas.bind("<Leave>", lambda _event: self._bind_wheel(False))
        self._rebuild_checks()

    def _size_checks(self, event: tk.Event[tk.Misc]) -> None:
        self.check_canvas.itemconfigure(self._check_window, width=event.width)

    def _bind_wheel(self, active: bool) -> None:
        if active:
            self.check_canvas.bind_all("<Button-4>", lambda _event: self.check_canvas.yview_scroll(-3, "units"))
            self.check_canvas.bind_all("<Button-5>", lambda _event: self.check_canvas.yview_scroll(3, "units"))
            self.check_canvas.bind_all("<MouseWheel>", self._mousewheel)
        else:
            self.check_canvas.unbind_all("<Button-4>")
            self.check_canvas.unbind_all("<Button-5>")
            self.check_canvas.unbind_all("<MouseWheel>")

    def _mousewheel(self, event: tk.Event[tk.Misc]) -> None:
        delta = getattr(event, "delta", 0)
        step = -1 if delta > 0 else 1
        self.check_canvas.yview_scroll(step * 3, "units")

    def _on_manual(self) -> None:
        if self._loading:
            return
        self.config.manual_override = bool(self.manual_var.get())
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
