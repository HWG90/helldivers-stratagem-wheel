"""The wheel opens from the last scan. Only the hotkey and SCAN read the screen."""

import threading

from PIL import Image

from stratagems.app import App
from stratagems.catalog import LoadoutEntry
from stratagems.config import Region
from stratagems.glyphs import ScanResult


class _InlineThread:
    def __init__(self, target: object = None, args: tuple[object, ...] = (), kwargs: dict[str, object] | None = None, daemon: bool | None = None) -> None:
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self) -> None:
        target = self._target
        if callable(target):
            target(*self._args, **self._kwargs)


def test_opening_the_wheel_does_not_scan_and_the_hotkey_does(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(threading, "Thread", _InlineThread)
    calls: list[str] = []

    def fake_scan_image(*_args: object, **_kwargs: object) -> ScanResult:
        calls.append("scan")
        return ScanResult(
            [LoadoutEntry("Resupply", ("down", "down", "up", "right"), "screen")],
            {},
            {},
        )

    monkeypatch.setattr("stratagems.app.scan_image", fake_scan_image)
    blank = lambda *_args, **_kwargs: Image.new("RGB", (8, 8), "black")
    monkeypatch.setattr("stratagems.app.capture_region", blank)
    monkeypatch.setattr("stratagems.settings.capture_region", blank)
    app = App(demo=True)
    try:
        if app.settings._preview_after is not None:
            app.root.after_cancel(app.settings._preview_after)
            app.settings._preview_after = None
        app.config.region = Region(0, 0, 20, 20)
        app._cache = [LoadoutEntry("Reinforce", ("up", "down", "right", "left", "up"), "screen")]
        app._cache_notice = "SCANNED · ON-SCREEN CODES"
        app.settings._crop = Image.new("RGB", (32, 32), "black")
        app.settings._paint_live_preview()
        assert app._cache[0].name == "Reinforce"

        app.present(0, 0, dry_run=True)
        assert calls == []
        assert app.overlay.entries[0].name == "Reinforce"

        app._on_mouse("mouse4", True, 0, 0)
        app.root.update()
        assert calls == ["scan"]
        assert app._cache[0].name == "Resupply"
        app._on_mouse("mouse4", False, 0, 0)
        app.root.update()
        assert calls == ["scan"]

        app.present(0, 0, dry_run=True)
        assert calls == ["scan"]
        assert app.overlay.entries[0].name == "Resupply"
    finally:
        app.root.destroy()


def test_an_empty_scan_keeps_the_saved_loadout(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(threading, "Thread", _InlineThread)
    calls: list[str] = []

    def fake_scan_image(*_args: object, **_kwargs: object) -> ScanResult:
        calls.append("scan")
        return ScanResult([], {}, {})

    monkeypatch.setattr("stratagems.app.scan_image", fake_scan_image)
    blank = lambda *_args, **_kwargs: Image.new("RGB", (8, 8), "black")
    monkeypatch.setattr("stratagems.app.capture_region", blank)
    monkeypatch.setattr("stratagems.settings.capture_region", blank)
    app = App(demo=True)
    try:
        if app.settings._preview_after is not None:
            app.root.after_cancel(app.settings._preview_after)
            app.settings._preview_after = None
        app.config.region = Region(0, 0, 20, 20)
        app._cache = [LoadoutEntry("Reinforce", ("up", "down", "right", "left", "up"), "screen")]
        app._cache_notice = "SCANNED · ON-SCREEN CODES"
        app._on_key("mouse4", True)
        app.root.update()
        assert calls == ["scan"]
        assert app._cache[0].name == "Reinforce"
    finally:
        app.root.destroy()
