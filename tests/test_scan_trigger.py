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
    captures = {"app": 0, "settings": 0}

    def fake_scan_image(*_args: object, **_kwargs: object) -> ScanResult:
        calls.append("scan")
        return ScanResult(
            [LoadoutEntry("Resupply", ("down", "down", "up", "right"), "screen")],
            {},
            {},
        )

    def app_capture(*_args: object, **_kwargs: object) -> Image.Image:
        captures["app"] += 1
        return Image.new("RGB", (8, 8), "black")

    def settings_capture(*_args: object, **_kwargs: object) -> Image.Image:
        captures["settings"] += 1
        return Image.new("RGB", (8, 8), "white")

    monkeypatch.setattr("stratagems.app.scan_image", fake_scan_image)
    monkeypatch.setattr("stratagems.app.capture_region", app_capture)
    monkeypatch.setattr("stratagems.settings.capture_region", settings_capture)
    app = App(demo=True)
    try:
        app.root.update()
        assert not app.root.tk.call("after", "info")
        assert captures == {"app": 0, "settings": 0}
        app.config.region = Region(0, 0, 20, 20)
        app._cache = [LoadoutEntry("Reinforce", ("up", "down", "right", "left", "up"), "screen")]
        app._cache_notice = "SCANNED · ON-SCREEN CODES"
        app.settings._crop = Image.new("RGB", (32, 32), "black")
        app.settings._refresh_preview()
        assert app._cache[0].name == "Reinforce"
        assert captures == {"app": 0, "settings": 0}

        app.present(0, 0, dry_run=True)
        app.root.update()
        assert calls == []
        assert captures == {"app": 0, "settings": 0}
        assert app.overlay.entries[0].name == "Reinforce"
        assert not app.root.tk.call("after", "info")

        app._on_mouse("mouse4", True, 0, 0)
        app.root.update()
        assert calls == ["scan"]
        assert captures == {"app": 1, "settings": 0}
        assert app._cache[0].name == "Resupply"
        assert app.settings._crop is not None
        assert app.settings._crop.size == (8, 8)
        app._on_mouse("mouse4", False, 0, 0)
        app.root.update()
        assert calls == ["scan"]
        assert captures["app"] == 1

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
        app.config.region = Region(0, 0, 20, 20)
        app._cache = [LoadoutEntry("Reinforce", ("up", "down", "right", "left", "up"), "screen")]
        app._cache_notice = "SCANNED · ON-SCREEN CODES"
        app._on_key("mouse4", True)
        app.root.update()
        assert calls == ["scan"]
        assert app._cache[0].name == "Reinforce"
        assert app.settings._crop is not None
        assert app.settings._crop.size == (8, 8)
    finally:
        app.root.destroy()


def test_preview_updates_on_slider_release_and_auto_without_replacing_the_loadout(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    paints: list[str] = []
    captures = {"settings": 0}

    def fake_preview(*_args: object, **_kwargs: object) -> tuple[Image.Image, str]:
        paints.append("paint")
        return Image.new("RGB", (4, 4), "black"), "right"

    def settings_capture(*_args: object, **_kwargs: object) -> Image.Image:
        captures["settings"] += 1
        return Image.new("RGB", (12, 12), "white")

    monkeypatch.setattr("stratagems.settings.arrow_preview", fake_preview)
    monkeypatch.setattr("stratagems.settings.capture_region", settings_capture)
    monkeypatch.setattr("stratagems.app.capture_region", lambda *_a, **_k: Image.new("RGB", (4, 4)))
    app = App(demo=True)
    try:
        app.root.update()
        assert paints == []
        assert captures["settings"] == 0
        assert not app.root.tk.call("after", "info")
        app.config.region = Region(0, 0, 20, 20)
        saved = [LoadoutEntry("Reinforce", ("up", "down", "right", "left", "up"), "screen")]
        app._cache = saved
        app.settings._crop = Image.new("RGB", (16, 16), "black")

        app.settings._on_hdr_slider("1.2")
        assert paints == []
        assert captures["settings"] == 0
        assert app._cache[0].name == "Reinforce"

        app.settings._finish_hdr_slider()
        assert paints == ["paint"]
        assert captures["settings"] == 0
        assert app._cache is saved

        app.settings._crop = None
        app.settings._auto_hdr()
        assert captures["settings"] == 1
        assert paints == ["paint", "paint"]
        assert app._cache[0].name == "Reinforce"
        assert not app.root.tk.call("after", "info")
    finally:
        app.root.destroy()
