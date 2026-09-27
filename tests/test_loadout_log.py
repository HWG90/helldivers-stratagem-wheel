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


def test_addon_uses_the_loader_log_and_does_not_scan_memory() -> None:
    source = MOD_LUA.read_text(encoding="utf-8")
    assert source.startswith(f"-- HD2-Addon: {RESOURCE}\n")
    assert len(f"-- HD2-Addon: {RESOURCE}\n".encode()) <= 256
    assert "EquippedStratagems.log" in source
    assert "CowboyBingusModLoader" in source
    assert "open_log" in source
    assert "print('[EquippedStratagems] loaded')" in source
    lowered = source.lower()
    for banned in ("readprocessmemory", "virtualquery", "getmodulehandle", "sigscan", "aob", "ffi"):
        assert banned not in lowered
    pairs = dict(re.findall(r'\["([^"]+)"\] = "([^"]+)"', source))
    expected = {
        normalize(alias): stratagem.name
        for stratagem in STRATAGEMS
        for alias in aliases(stratagem)
        if normalize(alias)
    }
    assert pairs == expected
    from mods.EquippedStratagems.build import OUTPUT, build, resource_hash

    built = build(OUTPUT)
    with zipfile.ZipFile(built) as package:
        names = set(package.namelist())
        assert "manifest.json" in names
        assert "INSTALL.txt" in names
        assert "Addon/9ba626afa44a3aa3.patch_0.stream" in names
        assert "Addon/9ba626afa44a3aa3.patch_0.gpu_resources" in names
        manifest = json.loads(package.read("manifest.json"))
        assert manifest["Name"] == "EquippedStratagems"
        assert manifest["Guid"] == "7f3a9c2e-6b14-4d58-8e21-0c5b9a4d71f6"
        assert manifest["Options"][0]["Include"] == ["Addon"]
        patches = [name for name in names if name.endswith(".patch_0")]
        assert len(patches) == 1
        blob = package.read(patches[0])
    assert f"-- HD2-Addon: {RESOURCE}\n".encode() in blob
    assert resource_hash(RESOURCE) > 0


def test_lua_mod_writes_catalog_names_when_the_loadout_changes(tmp_path: Path) -> None:
    aliases_path = tmp_path / "aliases.tsv"
    rows = [f"{alias}\t{stratagem.name}" for stratagem in STRATAGEMS for alias in aliases(stratagem)]
    aliases_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    script = r"""
local alias_file = arg[1]
local calls = 0
local bodies = {}
rawset(_G, 'CowboyBingusModLoader', {
    open_log = function(name)
        assert(name == 'EquippedStratagems.log')
        calls = calls + 1
        local file = { chunks = {} }
        function file:write(...)
            for index = 1, select('#', ...) do
                file.chunks[#file.chunks + 1] = select(index, ...)
            end
        end
        function file:close()
            bodies[#bodies + 1] = table.concat(file.chunks)
        end
        return file
    end,
})
local forwarded = nil
function update(dt, extra)
    forwarded = extra
end
dofile('mods/EquippedStratagems/EquippedStratagems.lua')
assert(EquippedStratagems.mod == 'EquippedStratagems')
assert(EquippedStratagems.api == 1)
for line in io.lines(alias_file) do
    local alias, name = line:match('^(.-)\t(.*)$')
    local got = EquippedStratagems.catalog_name(alias)
    if got ~= name then
        error('catalog mismatch for [' .. alias .. '] got ' .. tostring(got))
    end
end
update(0, 'marker')
assert(forwarded == 'marker')
assert(calls == 0)
_G.StratagemLoadout = {'not a stratagem'}
update(0.5, 'marker')
assert(calls == 0)
_G.StratagemLoadout = {'500kg', 'Autocannon', 'not a stratagem', 'resupply'}
update(0.5, 'again')
assert(bodies[#bodies] == 'Eagle 500kg Bomb\nAC-8 Autocannon\nResupply\n')
local after_first = calls
update(0.5, 'same')
assert(calls == after_first)
_G.StratagemLoadout = {'still not real'}
update(0.5, 'keep')
assert(calls == after_first)
_G.StratagemLoadout = {}
update(0.5, 'clear')
assert(bodies[#bodies] == '')
assert(EquippedStratagems.publish({'W.A.S.P. Launcher', '500 kg'}))
assert(bodies[#bodies] == 'StA-X3 W.A.S.P. Launcher\nEagle 500kg Bomb\n')
assert(not EquippedStratagems.publish({'nope'}))
assert(bodies[#bodies] == 'StA-X3 W.A.S.P. Launcher\nEagle 500kg Bomb\n')
local chained = update
dofile('mods/EquippedStratagems/EquippedStratagems.lua')
assert(update == chained)
print('lua-ok')
"""
    driver = tmp_path / "driver.lua"
    driver.write_text(script, encoding="utf-8")
    completed = subprocess.run(
        ["lua5.1", str(driver), str(aliases_path)],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "lua-ok" in completed.stdout
    assert "[EquippedStratagems] loaded" in completed.stdout
