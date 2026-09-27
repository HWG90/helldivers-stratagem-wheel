"""A loadout log fills the wheel. A missing or empty log leaves the scan path."""

import json
import re
import subprocess
import threading
import zipfile
from pathlib import Path

from PIL import Image

from stratagems.app import App
from stratagems.catalog import STRATAGEMS, LoadoutEntry
from stratagems.config import Region
from stratagems.glyphs import ScanResult
from stratagems.loadout_log import EQUIPPED_LOG_NAME, SLOTS_LOG_NAME, read_logged_loadout
from stratagems.matching import aliases, normalize

MOD_LUA = Path("mods/EquippedStratagems/EquippedStratagems.lua")
RESOURCE = "mods/EquippedStratagems/EquippedStratagems"


class _InlineThread:
    def __init__(self, target: object = None, args: tuple[object, ...] = (), kwargs: dict[str, object] | None = None, daemon: bool | None = None) -> None:
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self) -> None:
        target = self._target
        if callable(target):
            target(*self._args, **self._kwargs)


def _logs(tmp_path: Path) -> Path:
    directory = tmp_path / "CowboyBingus" / "Helldivers2" / "Logs"
    directory.mkdir(parents=True)
    return directory


def test_equipped_log_fills_the_wheel_without_duplicating_standing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _logs(tmp_path).joinpath(EQUIPPED_LOG_NAME).write_text(
        "500kg\nAC-8 Autocannon\nResupply\nresupply\n",
        encoding="utf-8",
    )
    app = App(demo=True)
    app.config.ocr_fallback = True
    try:
        app._cache = [LoadoutEntry("Eagle Airstrike", ("up", "right", "down", "right"), "screen")]
        app.present(0, 0, dry_run=True)
        assert [entry.name for entry in app.overlay.entries] == [
            "Reinforce",
            "Resupply",
            "Eagle 500kg Bomb",
            "AC-8 Autocannon",
        ]
        assert app.overlay.entries[0].code_source == "table"
        assert app.overlay.entries[2].code == ("up", "right", "down", "down", "down")
        assert "LOADOUT FILE" in app.overlay.notice
    finally:
        app.root.destroy()


def test_slots_log_wins_when_it_lists_names_and_garbage_does_not(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    logs = _logs(tmp_path)
    logs.joinpath(EQUIPPED_LOG_NAME).write_text("Eagle 500kg Bomb\n", encoding="utf-8")
    logs.joinpath(SLOTS_LOG_NAME).write_text("hello\nnot a stratagem\n", encoding="utf-8")
    assert [entry.name for entry in read_logged_loadout() or []] == ["Eagle 500kg Bomb"]

    logs.joinpath(SLOTS_LOG_NAME).write_text("Orbital Gatling Barrage\n", encoding="utf-8")
    assert [entry.name for entry in read_logged_loadout() or []] == ["Orbital Gatling Barrage"]


def test_empty_log_keeps_the_scan_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(threading, "Thread", _InlineThread)
    _logs(tmp_path).joinpath(EQUIPPED_LOG_NAME).write_text("\n# none\n", encoding="utf-8")
    calls: list[str] = []

    def fake_scan_image(*_args: object, **_kwargs: object) -> ScanResult:
        calls.append("scan")
        return ScanResult(
            [LoadoutEntry("Eagle Airstrike", ("up", "right", "down", "right"), "screen")],
            {},
            {},
        )

    monkeypatch.setattr("stratagems.app.scan_image", fake_scan_image)
    monkeypatch.setattr("stratagems.app.capture_region", lambda *_a, **_k: Image.new("RGB", (8, 8)))
    app = App(demo=True)
    app.config.ocr_fallback = True
    try:
        app.present(0, 0, dry_run=True)
        assert [entry.name for entry in app.overlay.entries] == ["Reinforce", "Resupply"]
        app.config.region = Region(0, 0, 20, 20)
        app._on_mouse("mouse4", True, 0, 0)
        app.root.update()
        app.present(0, 0, dry_run=True)
        assert calls == ["scan"]
        assert [entry.name for entry in app.overlay.entries] == ["Reinforce", "Resupply", "Eagle Airstrike"]
    finally:
        app.root.destroy()
