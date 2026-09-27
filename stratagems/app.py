"""Wire the terminal, the radial overlay, OCR, and key playback."""

from __future__ import annotations

# Tcl/Tk has to be pointed at the bundled libraries before tkinter loads.
# The Windows embeddable interpreter does not discover them on its own.
from stratagems.runtime import configure_bundled_runtime

configure_bundled_runtime()

import argparse
import threading
import time
import tkinter as tk
from pathlib import Path

from PIL import Image

from stratagems.binds import display_bind
from stratagems.catalog import MAX_WHEEL, LoadoutEntry, get
from stratagems.config import Config, load_config, save_config
from stratagems.cursor_pos import get_cursor, hide_cursor, set_cursor, show_cursor
from stratagems.listen import InputListener
from stratagems.game_focus import helldivers_focused
from stratagems.glyphs import cluster_glyphs
from stratagems.hdr import HdrCurve, curve_from_config
from stratagems.learn import LearnWindow
from stratagems.loadout_log import read_logged_loadout
from stratagems.ocr import OcrError, ScanResult, capture_region, save_bbox, scan_image
from stratagems.overlay import WHEEL_X, WHEEL_Y, RadialOverlay
from stratagems.placement import Monitor, list_monitors, wheel_top_left
from stratagems.pointer_lock import PointerLock
from stratagems.sender import KeyboardSender
from stratagems.sequence import execute_plan, format_plan, plan_input
from stratagems.settings import SettingsHooks, SettingsWindow
from stratagems.theme import BG


class App:
    def __init__(self, *, demo: bool) -> None:
        self.demo = demo
        self.config, self._load_warning = load_config()
        self._fire_dry = demo
        self._radial_down = False
        self._lock = PointerLock(
            get_cursor,
            set_cursor,
            hide_cursor=hide_cursor,
            show_cursor=show_cursor,
        )
        self._held_offset = (0, 0)
        self._scan_gen = 0
        self._learn_window: LearnWindow | None = None
        self._cache: list[LoadoutEntry] = []
        self._cache_notice = ""
        self._capture_cb: object = None
        self._capture_ready = False
        self._send_lock = threading.Lock()
        self._keyboard: KeyboardSender | None = None
        self.listener: InputListener | None = None
        self._game_focused = helldivers_focused

        self.root = tk.Tk()
        self.root.title("Stratagem Terminal")
        self.root.configure(bg=BG)
        self.root.geometry("940x1080+24+24")
        self.root.minsize(780, 820)
        self.settings = SettingsWindow(
            self.root,
            self.config,
            SettingsHooks(
                on_changed=self._on_changed,
                on_rescan=self.rescan,
                on_learn=self.learn,
                on_preview=self.preview,
                arm_capture=self.arm_capture,
            ),
            demo=demo,
        )
        self.overlay = RadialOverlay(self.root, on_confirm=self._confirm_current, on_cancel=self._cancel_wheel)
        self.overlay.set_transparent(self.config.transparent_wheel)
        self.root.protocol("WM_DELETE_WINDOW", self.root.quit)
        self._set_initial_status()

    def run(self, dump: Path | None = None) -> None:
        self._start_listener()
        if dump is not None:
            self._dump_dir = dump
            self.root.after(500, self._dump_screenshots)
        elif self.demo:
            self.root.after(200, self._open_demo)
        try:
            self.root.mainloop()
        finally:
            self._lock.release()
            show_cursor()
            if self.listener is not None:
                self.listener.stop()

    def preview(self) -> None:
        self._radial_down = False
        if self._lock.active:
            self._lock.release()
        self.overlay.set_pointer_locked(False)
        left, top = self._centered_on_cursor()
        self.present(left, top, dry_run=True)

    def rescan(self) -> None:
        if self.config.manual_override:
            self.settings.set_status("Manual override is on, so the scan is skipped.")
            return
        if self.config.region is None:
            self.settings.set_status("Calibrate the stratagem list before scanning.")
            return
        self.scan()

    def arm_capture(self, callback: object) -> None:
        self._capture_cb = callback
        self._capture_ready = False
        self.root.after(250, self._mark_capture_ready)

    def present(self, left: int, top: int, *, dry_run: bool) -> None:
        self._fire_dry = dry_run
        entries, notice = self._immediate_state()
        self.overlay.show(
            left,
            top,
            entries,
            notice,
            demo=self.demo,
            bind_label=display_bind(self.config.radial_bind),
        )
    def scan(self) -> None:
        """Read the calibrated region once. Opening the wheel does not call this."""
        region = self.config.region
        if region is None:
            return
        self._scan_gen += 1
        generation = self._scan_gen
        glyph_lut = {key: list(value) for key, value in self.config.glyph_lut.items()}
        icon_lut = dict(self.config.icon_lut)
        hdr = self.config.hdr
        curve = curve_from_config(self.config)
        self.settings.set_status("Scanning the stratagem list…")

        def work() -> None:
            image: Image.Image | None = None
            try:
                image = capture_region(region.left, region.top, region.width, region.height)
                result = scan_image(
                    image,
                    hdr=hdr,
                    curve=curve,
                    glyph_lut=glyph_lut,
                    icon_lut=icon_lut,
                )
                error = None
            except (OcrError, OSError) as exc:
                result = None
                error = str(exc)
            self._later(
                lambda result=result, error=error, generation=generation, image=image: self._apply_scan(
                    generation, result, error, image
                )
            )

        threading.Thread(target=work, daemon=True).start()

    def learn(self) -> None:
        """Capture arrow glyphs once and ask the user to tag each unique shape."""
        region = self.config.region
        if region is None:
            self.settings.set_status("Calibrate the stratagem list before Learn.")
            return
        hdr = self.config.hdr
        curve = curve_from_config(self.config)
        self.settings.set_status("Reading arrow shapes to learn…")

        def work() -> None:
            try:
                image: Image.Image | None = capture_region(region.left, region.top, region.width, region.height)
                error = None
            except (OcrError, OSError) as exc:
                image = None
                error = str(exc)
            self._later(
                lambda image=image, error=error: self._open_learn(image, error, hdr, curve)
            )

        threading.Thread(target=work, daemon=True).start()

    def _open_learn(
        self,
        image: Image.Image | None,
        error: str | None,
        hdr: bool,
        curve: HdrCurve,
    ) -> None:
        if error or image is None:
            message = error or "Could not capture the stratagem list."
            self.settings.set_status(message)
            self.settings.append_log(message)
            return
        clusters = cluster_glyphs(image, hdr=hdr, curve=curve)
        if not clusters:
            self.settings.set_status("Learn found no arrow glyphs in the calibrated region.")
            return
        self._learn_window = LearnWindow(self.root, clusters, self._save_learned)
        self.settings.set_status(f"Tag {len(clusters)} arrow shapes, then save.")

    def _save_learned(self, glyph_lut: dict[str, list[str]]) -> None:
        self.config.glyph_lut = glyph_lut
        save_config(self.config)
        count = sum(len(samples) for samples in glyph_lut.values())
        self.settings.set_status(f"Saved {count} arrow samples. Scan will use these shapes.")
        self.settings.append_log(f"Learn saved {count} arrow samples.")

    def _open_demo(self) -> None:
        self.overlay.set_pointer_locked(False)
        left, top = self._centered_on_cursor()
        self.present(left, top, dry_run=True)

    def _dump_screenshots(self) -> None:
        self._dump_dir.mkdir(parents=True, exist_ok=True)
        left, top = self._centered_on_cursor()
        self.present(left, top, dry_run=True)
        self.overlay.set_highlight(0)
        self.root.update_idletasks()
        self.root.update()
        self.root.after(400, self._capture_dump)

    def _capture_dump(self) -> None:
        directory = self._dump_dir
        try:
            self.overlay.set_highlight(0)
            self.root.update()
            _grab(self.overlay.win, directory / "radial-demo.png")
            self.overlay.hide()
            self.root.update()
            _grab(self.root, directory / "settings-window.png")
            print(f"wrote screenshots to {directory}", flush=True)
        except Exception as exc:
            print(f"screenshot failed: {exc}", flush=True)
        finally:
            self.root.quit()

    def _immediate_state(self) -> tuple[list[LoadoutEntry], str]:
        if self.config.manual_override:
            pinned = _pinned(self.config)
            entries = _wheel_entries(pinned)
            if not pinned:
                return entries, _STANDING_NOTICE
            notice = "MANUAL LOADOUT"
            names = {entry.name.casefold() for entry in _standing_entries()}
            names.update(entry.name.casefold() for entry in pinned)
            if len(names) > MAX_WHEEL:
                notice += f" · SHOWING {MAX_WHEEL}"
            return entries, notice
        logged = read_logged_loadout()
        if logged:
            return _wheel_entries(logged), _file_notice(logged)
        if self._cache:
            return _wheel_entries(self._cache), self._cache_notice
        return _standing_entries(), _STANDING_NOTICE

    def _apply_scan(
        self,
        generation: int,
        result: ScanResult | None,
        error: str | None,
        image: Image.Image | None = None,
    ) -> None:
        if generation != self._scan_gen:
            return
        if image is not None:
            self.settings.show_capture(image)
        if error or result is None:
            message = error or "Scan failed."
            self.settings.set_status(message)
            self.settings.append_log(f"Scan failed: {message}")
            if self.overlay.visible and not self._cache and not self.config.manual_override:
                standing, notice = self._immediate_state()
                self.overlay.set_state(standing, notice, display_bind(self.config.radial_bind))
            return
        entries = list(result.entries)
        if not entries:
            reason = result.failure or (
                "Scan found nothing: no rows, the arrow confidence was too low, or the text was empty."
            )
            if self._cache:
                message = f"{reason} The last mission loadout is unchanged."
            else:
                message = reason
                if self.overlay.visible and not self.config.manual_override:
                    standing, notice = self._immediate_state()
                    self.overlay.set_state(standing, notice, display_bind(self.config.radial_bind))
            self.settings.set_status(message)
            self.settings.append_log(message)
            return
        self.config.glyph_lut = dict(result.glyph_lut)
        self.config.icon_lut = dict(result.icon_lut)
        save_config(self.config)
        total = len(entries)
        notice = _scan_notice(entries, total)
        self._cache = entries
        self._cache_notice = notice
        shown = _wheel_entries(entries)
        if self.overlay.visible and not self.config.manual_override:
            self.overlay.set_state(shown, notice, display_bind(self.config.radial_bind))
        names = ", ".join(entry.name for entry in entries) or "none"
        noun = "stratagem" if total == 1 else "stratagems"
        status = f"Scan found {total} {noun}."
        if result.note:
            status = f"{status} {result.note}"
        self.settings.set_status(status)
        self.settings.append_log(f"Scan ({total}): {names}")
        if result.note:
            self.settings.append_log(result.note)

    def _confirm_current(self) -> None:
        if not self.overlay.visible:
            return
        entry = self.overlay.selected()
        self.overlay.hide()
        self._radial_down = False
        if entry is None:
            self.settings.set_status("Cancelled.")
            self.settings.append_log("Cancelled.")
            return
        self._fire(entry)

    def _cancel_wheel(self) -> None:
        self._radial_down = False
        self._lock.release()
        if not self.overlay.visible:
            return
        self.overlay.hide()
        self.settings.set_status("Cancelled.")

    def _fire(self, entry: LoadoutEntry) -> None:
        dry = self._fire_dry
        steps = plan_input(
            entry.code,
            modifier=self.config.modifier,
            style=self.config.direction_style,
            start_delay_ms=self.config.start_delay_ms,
            gap_ms=self.config.gap_ms,
            tail_ms=self.config.tail_ms,
            tap_ms=self.config.tap_ms,
        )
        text = format_plan(steps, name=entry.name, code=entry.code)
        self.settings.append_log(text)
        print(text, flush=True)
        if dry:
            self.settings.set_status(f"Dry run: {entry.name}")
            return
        sender = self._sender()
        self.settings.set_status(f"Sending {entry.name}")

        def work() -> None:
            with self._send_lock:
                try:
                    execute_plan(steps, sender, sleep=time.sleep, now=time.perf_counter)
                except Exception as exc:
                    self._later(lambda: self.settings.set_status(f"Input failed: {exc}"))
                    return
            self._later(lambda: self.settings.set_status(f"Sent {entry.name}"))

        threading.Thread(target=work, daemon=True).start()

    def _sender(self) -> KeyboardSender:
        if self._keyboard is None:
            self._keyboard = KeyboardSender()
        return self._keyboard

    def _on_changed(self) -> None:
        path = save_config(self.config)
        self.overlay.set_transparent(self.config.transparent_wheel)
        self.settings.set_status(f"Saved {path}")
        if self.overlay.visible:
            entries, notice = self._immediate_state()
            self.overlay.set_state(entries, notice, display_bind(self.config.radial_bind))

    def _game_is_focused(self) -> bool:
        try:
            return bool(self._game_focused())
        except OSError:
            return False

    def _press_radial(self, x: int, y: int) -> None:
        if self._capture_cb is not None:
            if self._lock.active:
                self._lock.release()
            return
        if self._radial_down:
            return
        if not self._game_is_focused():
            if self._lock.active:
                self._lock.release()
            return
        if not self._lock.active:
            return
        anchor = self._lock.anchor
        if anchor is None:
            anchor = (x, y)
        self._radial_down = True
        self.overlay.set_pointer_locked(True)
        left, top = wheel_top_left(anchor[0], anchor[1], self._monitors(), WHEEL_X, WHEEL_Y)
        self.present(left, top, dry_run=self.demo)
        dx, dy = self._lock.offset
        self.overlay.apply_offset(dx, dy)
        self.root.after(100, self._watch_game_focus)

    def _watch_game_focus(self) -> None:
        if not self._radial_down:
            return
        if not self._game_is_focused():
            self._cancel_wheel()
            return
        self.root.after(100, self._watch_game_focus)

    def _release_radial(self) -> None:
        if not self._radial_down:
            return
        if not self._game_is_focused():
            self._cancel_wheel()
            return
        self._radial_down = False
        if self._lock.active:
            released = self._lock.release()
            if released is not None:
                self._held_offset = released
        dx, dy = self._held_offset
        self.overlay.apply_offset(dx, dy)
        self._confirm_current()

    def _on_mouse(self, name: str, pressed: bool, x: int, y: int) -> None:
        if self._capture_ready and pressed:
            self._finish_capture(name)
            return
        if name == self.config.radial_bind:
            if pressed:
                self._press_radial(x, y)
            else:
                self._release_radial()
            return
        if name == self.config.rescan_bind and pressed:
            self.rescan()
        if name == self.config.learn_bind and pressed:
            self.learn()

    def _on_key(self, name: str, pressed: bool) -> None:
        if self._capture_ready and pressed:
            self._finish_capture(None if name == "esc" else name)
            return
        if name == "esc" and pressed:
            self._cancel_wheel()
            return
        if name == self.config.radial_bind:
            if pressed:
                pointer = self.listener.pointer if self.listener is not None else (0, 0)
                self._press_radial(pointer[0], pointer[1])
            else:
                self._release_radial()
            return
        if name == self.config.rescan_bind and pressed:
            self.rescan()
        if name == self.config.learn_bind and pressed:
            self.learn()

    def _finish_capture(self, name: str | None) -> None:
        callback = self._capture_cb
        self._capture_cb = None
        self._capture_ready = False
        self._radial_down = False
        if self._lock.active:
            self._lock.release()
        if callable(callback):
            callback(name)

    def _mark_capture_ready(self) -> None:
        if self._capture_cb is not None:
            self._capture_ready = True
            self.settings.set_status("Listening for the new bind. Escape cancels.")

    def _start_listener(self) -> None:
        try:
            self.listener = InputListener(self._from_mouse, self._from_key, self._from_move)
            self.listener.start()
            self.overlay.external_bind = True
        except Exception as exc:
            self.listener = None
            self.settings.set_status(
                f"Global input hook unavailable ({exc}). Use Preview wheel; demo clicks still work."
            )

    def _from_mouse(self, name: str, pressed: bool, x: int, y: int) -> None:
        if self._capture_cb is None and name == self.config.radial_bind:
            if pressed:
                self._arm_hold((x, y))
            elif self._lock.active:
                released = self._lock.release()
                if released is not None:
                    self._held_offset = released
        self._later(lambda name=name, pressed=pressed, x=x, y=y: self._on_mouse(name, pressed, x, y))

    def _from_key(self, name: str, pressed: bool) -> None:
        if self._capture_cb is None and name == "esc" and pressed and self._lock.active:
            self._lock.release()
        elif self._capture_cb is None and name == self.config.radial_bind:
            if pressed:
                point = self.listener.pointer if self.listener is not None else (0, 0)
                self._arm_hold(point)
            elif self._lock.active:
                released = self._lock.release()
                if released is not None:
                    self._held_offset = released
        self._later(lambda name=name, pressed=pressed: self._on_key(name, pressed))

    def _from_move(self, x: int, y: int) -> None:
        if not self._lock.active:
            return
        if not self._game_is_focused():
            self._later(self._cancel_wheel)
            return
        dx, dy = self._lock.observe(x, y)
        self._later(lambda dx=dx, dy=dy: self._apply_hold_offset(dx, dy))

    def _arm_hold(self, fallback: tuple[int, int]) -> None:
        if self._capture_cb is not None or self._lock.active or self._radial_down:
            return
        if not self._game_is_focused():
            return
        self._held_offset = (0, 0)
        self._lock.engage(fallback)

    def _apply_hold_offset(self, dx: int, dy: int) -> None:
        if not self._lock.active or not self._radial_down or not self.overlay.visible:
            return
        self.overlay.apply_offset(dx, dy)

    def _centered_on_cursor(self) -> tuple[int, int]:
        x, y = self._cursor_point()
        return wheel_top_left(x, y, self._monitors(), WHEEL_X, WHEEL_Y)

    def _cursor_point(self) -> tuple[int, int]:
        try:
            return get_cursor()
        except Exception:
            if self.listener is not None:
                return self.listener.pointer
            pointer_x, pointer_y = self.root.winfo_pointerxy()
            return int(pointer_x), int(pointer_y)

    def _monitors(self) -> list[Monitor]:
        found = list_monitors()
        if found:
            return found
        width = max(1, int(self.root.winfo_screenwidth()))
        height = max(1, int(self.root.winfo_screenheight()))
        return [Monitor(0, 0, width, height)]

    def _later(self, callback: object) -> None:
        try:
            self.root.after(0, callback)
        except tk.TclError:
            return

    def _set_initial_status(self) -> None:
        if self._load_warning:
            self.settings.set_status(self._load_warning)
            return
        if self.demo:
            self.settings.set_status(
                "Demo mode. Reinforce and Resupply are on the wheel. Confirming a wedge logs the keys and does not send them."
            )
            return
        self.settings.set_status(
            "Hold Mouse3 to open the wheel. Mouse5 learns arrow shapes. Mouse4 scans. Escape cancels."
        )


_STANDING_NAMES = ("Reinforce", "Resupply")
_STANDING_NOTICE = "REINFORCE AND RESUPPLY · SCAN ADDS THE MISSION LOADOUT"
_FILE_NOTICE = "LOADOUT FILE · CATALOG CODES"


def _file_notice(entries: list[LoadoutEntry]) -> str:
    notice = _FILE_NOTICE
    seen = {entry.name.casefold() for entry in _standing_entries()}
    total = len(seen)
    for entry in entries:
        key = entry.name.casefold()
        if key not in seen:
            seen.add(key)
            total += 1
    if total > MAX_WHEEL:
        notice += f" · SHOWING {MAX_WHEEL}"
    return notice


def _standing_entries() -> list[LoadoutEntry]:
    """Catalog codes for the stratagems that are always on the wheel."""
    entries: list[LoadoutEntry] = []
    for name in _STANDING_NAMES:
        item = get(name)
        if item is None:
            continue
        entries.append(LoadoutEntry(item.name, item.code, "table"))
    return entries


def _wheel_entries(extra: list[LoadoutEntry]) -> list[LoadoutEntry]:
    """Reinforce and Resupply, then the mission loadout, each name once."""
    merged = _standing_entries()
    seen = {entry.name.casefold() for entry in merged}
    for entry in extra:
        key = entry.name.casefold()
        if key in seen:
            continue
        seen.add(key)
        merged.append(entry)
    return merged[:MAX_WHEEL]


def _pinned(config: Config) -> list[LoadoutEntry]:
    entries: list[LoadoutEntry] = []
    for name in config.pinned:
        item = get(name)
        if item is None:
            continue
        entries.append(LoadoutEntry(item.name, item.code, "manual"))
    return entries


def _scan_notice(entries: list[LoadoutEntry], total: int) -> str:
    if total == 0:
        return "NO STRATAGEMS RECOGNIZED"
    sources = {entry.code_source for entry in entries}
    if sources == {"screen"}:
        notice = "SCANNED · ON-SCREEN CODES"
    elif "screen" in sources:
        notice = "SCANNED · ON-SCREEN CODES WHERE READ"
    else:
        notice = "SCANNED · TABLE CODES"
    if total > MAX_WHEEL:
        notice += f" · SHOWING {MAX_WHEEL} OF {total}"
    return notice


def _grab(widget: tk.Misc, path: Path) -> None:
    widget.update_idletasks()
    left = int(widget.winfo_rootx())
    top = int(widget.winfo_rooty())
    width = int(widget.winfo_width())
    height = int(widget.winfo_height())
    if width < 2 or height < 2:
        raise RuntimeError(f"{path.name} window is not mapped ({width}x{height})")
    save_bbox(left, top, width, height, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m stratagems",
        description="Helldivers 2 stratagem wheel. Screen capture and ordinary keypresses only.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Open the sample wheel and log the key sequence instead of sending it",
    )
    parser.add_argument("--dump-screenshots", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    demo = bool(args.demo or args.dump_screenshots is not None)
    App(demo=demo).run(dump=args.dump_screenshots)
    return 0
