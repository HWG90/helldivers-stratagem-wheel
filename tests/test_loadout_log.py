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


def test_addon_uses_the_loader_log_and_reads_player_state() -> None:
    source = MOD_LUA.read_text(encoding="utf-8")
    assert source.startswith(f"-- HD2-Addon: {RESOURCE}\n")
    assert len(f"-- HD2-Addon: {RESOURCE}\n".encode()) <= 256
    assert "EquippedStratagems.log" in source
    assert "CowboyBingusModLoader" in source
    assert "open_log" in source
    assert "print('[EquippedStratagems] loaded')" in source
    assert "mods/codex/loadouts" in source
    assert "0x348e8f8" in source
    assert "0x37cb600" in source
    assert "0x33266a0" in source
    assert "0x3326468" in source
    assert "0x347cf18" in source
    assert "0x1D0" in source
    assert "686968" in source
    assert "left ctrl" in source
    assert "GetAsyncKeyState" in source
    assert "0xA2" in source
    assert "0x33266b0" not in source
    assert "GetModuleHandleA" in source
    assert "ReadProcessMemory" in source
    assert "register_binding" in source
    assert "equippedstratagems.send_strategems" in source
    assert "Send Strategems" in source
    assert "script/lua/player" not in source
    lowered = source.lower()
    for banned in ("virtualquery", "writeprocessmemory", "virtualprotect", "sigscan", "aob"):
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
local GAME = 0x10000000
local BUFFER = 0x20000000
local PM = 0x30000000
local ENTITY = 0x31000000
local SM = 0x32000000
local ROWS = 0x33000000
local MODE = 0x34000000
local function u32s(n)
    return string.char(
        n % 256,
        math.floor(n / 256) % 256,
        math.floor(n / 65536) % 256,
        math.floor(n / 16777216) % 256)
end
local function u64s(n) return u32s(n) .. u32s(0) end
local function overlay(buf, offset, bytes)
    return buf:sub(1, offset) .. bytes .. buf:sub(offset + #bytes + 1)
end
local group_sizes = {7204, 1184, 5860, 5228, 19152, 7040, 3832, 18344, 4884, 1104, 6444}
local group_counts = {13, 2, 11, 9, 36, 13, 7, 34, 9, 2, 13}
local named = {[1] = '500kg', [2] = 'Autocannon', [5] = 'Resupply'}
local parts, table_slots = {}, {}
local function add(bytes) parts[#parts + 1] = bytes end
add(u32s(11))
local offset, kind = 4, 0
for group = 1, 11 do
    local size, count = group_sizes[group], group_counts[group]
    add(u32s(0x444C444C))
    add(u32s(1))
    add(u32s(0x30EB6399))
    add(u32s(size - 24))
    add(u32s(1))
    add(u32s(0))
    add(u64s(BUFFER + offset + 40))
    add(u32s(count))
    add(u32s(0))
    for index = 0, count - 1 do
        kind = kind + 1
        local record_at = offset + 40 + index * 400
        table_slots[kind] = BUFFER + record_at
        add(u32s(kind))
        local label = named[kind]
        if label then
            add(label)
            add(string.char(0))
            add(string.rep(string.char(255), 400 - 4 - #label - 1))
        else
            add(string.rep(string.char(255), 396))
        end
    end
    add(string.rep(string.char(255), size - (40 + count * 400)))
    offset = offset + size
end
local settings = table.concat(parts)
assert(#settings == 80280 and kind == 149, 'settings image does not match the stratagem buffer')
local table_parts = {}
for slot = 0, 149 do table_parts[slot + 1] = u64s(table_slots[slot] or 0) end
local settings_table = table.concat(table_parts)
local OWNER = 0x50000000
local DMAP = 0x51000000
local CTRL_ID = 41
local player = string.rep('\0', 0x440)
local entity = overlay(string.rep('\0', 24), 20, '\1')
local regions = {
    {addr = GAME + 0x348e8f8, bytes = u64s(BUFFER)},
    {addr = GAME + 0x37cb600, bytes = settings_table},
    {addr = GAME + 0x3326468, bytes = u64s(PM)},
    {addr = BUFFER, bytes = settings},
    {addr = PM, bytes = player},
    {addr = ENTITY, bytes = entity},
}
local key_down = false
local function read_region(addr, size)
    for index = #regions, 1, -1 do
        local region = regions[index]
        local delta = addr - region.addr
        if delta >= 0 and delta + size <= #region.bytes then
            return region.bytes:sub(delta + 1, delta + size)
        end
    end
    return nil
end
local function pointer_of(bytes, pointer_offset)
    pointer_offset = pointer_offset or 0
    local packed = bytes:sub(pointer_offset + 1, pointer_offset + 8)
    if #packed < 8 then return nil end
    local value = 0
    for index = 8, 1, -1 do value = value * 256 + packed:byte(index) end
    if value < 0x10000 then return nil end
    return value
end
local function install_reader()
    _G.EquippedStratagemsReader = {
        module = function(name) assert(name == 'game.dll'); return GAME end,
        read = read_region,
        pointer = pointer_of,
        key_down = function(vk)
            assert(vk == 0xA2 or vk == 0xA3 or vk == 0x11)
            return key_down
        end,
    }
end
local function put_region(addr, bytes)
    regions[#regions + 1] = {addr = addr, bytes = bytes}
end
-- Thrown-ball rows. The log must not pick these up.
local thrown = overlay(overlay(string.rep('\0', 0x80), 0x34, u32s(1)), 0x78, u64s(ROWS))
local thrown_row = overlay(string.rep('\0', 64), 12, u32s(5))
put_region(GAME + 0x33266b0, u64s(SM))
put_region(SM, thrown)
put_region(ROWS, thrown_row)
local function use_slots(kinds, mission_type, menu, action)
    local mode = string.rep('\0', 0x44)
    if mission_type > 0 then
        mode = overlay(mode, 8, u32s(1))
        mode = overlay(mode, 0x40, u32s(mission_type))
    end
    local slots = string.rep('\0', 0x440)
    local at = 0x1D0
    for _, kind in ipairs(kinds) do
        slots = overlay(slots, at, u32s(kind))
        at = at + 4
    end
    put_region(GAME + 0x33266a0, u64s(MODE))
    put_region(MODE, mode)
    put_region(PM, slots)
    key_down = menu == 'key'
    local owner = string.rep('\0', 687000)
    if action then
        owner = overlay(owner, 686968, u64s(DMAP))
        owner = overlay(owner, 686976, u32s(256))
        local mapping = string.char(0x43, 0xff, 0, 0, CTRL_ID, 0, 0, 0) .. u32s(2) .. string.rep('\0', 8)
        local record = u32s(65536 + 3) .. u32s(1) .. mapping .. string.rep('\0', 328 - 8 - #mapping)
        put_region(DMAP, record .. string.rep('\0', 256 * 328 - #record))
        local state_at = 808 + 32 * (97 + 3)
        owner = overlay(owner, state_at, menu == 'action' and '\1' or '\0')
        put_region(GAME + 0x347cf18, u64s(OWNER))
        put_region(OWNER, owner)
        _G.stingray = {Keyboard = {button_id = function(name)
            if name == 'left ctrl' then return CTRL_ID end
            return nil
        end}}
    else
        _G.stingray = nil
        put_region(GAME + 0x347cf18, u64s(0))
    end
    install_reader()
end
update(0, 'marker')
assert(forwarded == 'marker')
assert(calls == 1)
assert(bodies[#bodies] == '# loadouts=no\n# game.dll=no\n# menu=closed\n# slots=unread\n')
_G.EquippedStratagemsReader = {
    module = function() return nil end,
    read = function() return nil end,
    pointer = function() return nil end,
}
update(0.5, 'unreadable')
assert(calls == 1)
use_slots({1, 2}, 0, 'key', false)
update(0.5, 'ship-menu')
assert(bodies[#bodies] == '# loadouts=no\n# game.dll=yes\n# menu=open\n# slots=2\n')
assert(not bodies[#bodies]:find('Eagle', 1, true))
use_slots({3}, 1, 'key', false)
update(0.5, 'unknown-slot')
assert(bodies[#bodies] == '# loadouts=no\n# game.dll=yes\n# menu=open\n# slots=unread\n')
use_slots({1, 2}, 1, 'key', false)
update(0.5, 'menu-open')
assert(bodies[#bodies] == 'Eagle 500kg Bomb\nAC-8 Autocannon\n')
local after_first = calls
key_down = false
update(0.5, 'menu-closed')
assert(calls == after_first)
assert(bodies[#bodies] == 'Eagle 500kg Bomb\nAC-8 Autocannon\n')
use_slots({3}, 1, 'key', false)
update(0.5, 'keep')
assert(calls == after_first)
assert(bodies[#bodies] == 'Eagle 500kg Bomb\nAC-8 Autocannon\n')
package.loaded['mods/codex/loadouts'] = {current = {'Orbital Gatling Barrage'}}
update(0.5, 'loadouts-ignored')
assert(calls == after_first)
assert(bodies[#bodies] == 'Eagle 500kg Bomb\nAC-8 Autocannon\n')
assert(EquippedStratagems.publish({'W.A.S.P. Launcher', '500 kg'}))
assert(bodies[#bodies] == 'StA-X3 W.A.S.P. Launcher\nEagle 500kg Bomb\n')
assert(not EquippedStratagems.publish({'nope'}))
assert(bodies[#bodies] == 'StA-X3 W.A.S.P. Launcher\nEagle 500kg Bomb\n')
local registered_label = nil
local down = false
_G.ModBindingsMenu = {
    api = 1,
    register_binding = function(id, label, slot, options)
        assert(id == 'equippedstratagems.send_strategems')
        assert(label == 'Send Strategems')
        assert(slot == nil)
        assert(type(options) == 'table' and options.category == 'EquippedStratagems')
        registered_label = label
        return true
    end,
    is_down = function(id)
        assert(id == 'equippedstratagems.send_strategems')
        return down
    end,
}
update(0.1, 'bind-register')
assert(registered_label == 'Send Strategems')
package.loaded['mods/codex/loadouts'] = nil
use_slots({5, 1}, 1, 'action', true)
down = true
local before_binding = calls
update(0.1, 'bind-fire')
assert(calls > before_binding)
assert(bodies[#bodies] == 'Resupply\nEagle 500kg Bomb\n')
down = false
key_down = false
update(0.1, 'bind-up')
use_slots({1, 2}, 1, 'closed', true)
update(0.1, 'action-up')
use_slots({1, 2}, 1, 'action', true)
local before_action = calls
update(0.1, 'action-down')
assert(calls > before_action)
assert(bodies[#bodies] == 'Eagle 500kg Bomb\nAC-8 Autocannon\n')
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
