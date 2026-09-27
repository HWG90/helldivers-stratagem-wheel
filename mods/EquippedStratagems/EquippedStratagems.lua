-- HD2-Addon: mods/EquippedStratagems/EquippedStratagems

-- Writes equipped stratagems, one catalog name per line, for the stratagem wheel.
-- Bingus Shared Loader discovers this entry, opens the log, and chains update.
-- Send Strategems is a Mod Bindings Menu binding. This file does not patch
-- code, signature-scan, or hide itself.
--
-- The first update always creates EquippedStratagems.log. Until catalog
-- names are known the file is status lines (a leading #, which the wheel
-- ignores). Names replace that status, one catalog name per line.
-- mods/codex/loadouts is a compiled patch, so it is only reported, never
-- called.
--
-- The in-game stratagem menu (default hold Left Ctrl) is an input action,
-- not a scancode. ModBindingsMenu's input owner is *(game+0x347cf18).
-- Shipped defaults are the 256 records at owner+686968. A keyboard button
-- mapping has device nibble 3 and button-input nibble 4; the Stingray key
-- id is byte 4. Left Ctrl's id comes from stingray.Keyboard.button_id
-- ("left ctrl", "lctrl", "left control"). Hold mappings (trigger u32 2 at
-- mapping+8) win. The menu is open while that action's state byte at
-- owner+808+32*(97*group+action) is nonzero, so a rebound or a controller
-- still counts. If that action cannot be resolved, GetAsyncKeyState of
-- VK_LCONTROL (0xA2), VK_RCONTROL (0xA3), or VK_CONTROL (0x11) is the
-- fallback, the same call GalacticMenuHotkey uses.
--
-- Names are the equipped slots the menu shows, read only in mission mode
-- 1..7 (*(game+0x33266a0), ShallowWaterDiving / spawn_data). They live on
-- the player block *(game+0x3326468) that those mods already read, in the
-- span after the countdown at +0x12C and before state at +0x2E0 (and the
-- tail after the use bit at +0x3B4). Each slot list there is a stingray
-- array: u32 count, u32 capacity, then a pointer to packed StratagemInfo
-- kind ids or to StratagemInfo records from game+0x37cb600. The old inline
-- kinds at player+0x1D0 are empty on this build and are not the list. The
-- thrown ball list is not this loadout either. StratagemInfo names are
-- *(game+0x348e8f8), table game+0x37cb600 (navigation_patch).
-- game.dll is tonumber(GetModuleHandleA('game.dll')); each read is
-- ReadProcessMemory of a const void*.

local prior = rawget(_G, 'EquippedStratagems')
if type(prior) == 'table' and prior.mod == 'EquippedStratagems' then return end

local LOG_NAME = 'EquippedStratagems.log'
local RESOURCE = 'mods/EquippedStratagems/EquippedStratagems'
local LOADOUTS_MODULE = 'mods/codex/loadouts'
local BINDING_ID = 'equippedstratagems.send_strategems'
local BINDING_LABEL = 'Send Strategems'
local POLL_SECONDS = 0.5
local SETTINGS_RVA = 0x348e8f8
local TABLE_RVA = 0x37cb600
local MISSION_RVA = 0x33266a0
local PLAYER_RVA = 0x3326468
local INPUT_OWNER_RVA = 0x347cf18
local SETTINGS_SIZE = 80280
local RECORD_SIZE = 400
local MAX_EQUIPPED = 16
-- Inline kinds at this offset are empty on the current build. Arrays that
-- start here are not the equipped list.
local EMPTY_SLOT_OFFSET = 0x1D0
local ARRAY_SPANS = {{0x130, 0x2E0}, {0x3B8, 0x440}}
local MIN_LOADOUT = 2
local MAX_CAPACITY = 32
local DEFAULTS_MAP = 686968
local ACTION_STATE_OFFSET = 808
local ACTION_STATE_STRIDE = 32
local BINDING_RECORD = 328
local MAPPING_SIZE = 20
local HOLD_TRIGGER = 2
local KEYBOARD_DEVICE = 3
local BUTTON_INPUT = 4
local VK_LCONTROL = 0xA2
local VK_RCONTROL = 0xA3
local VK_CONTROL = 0x11
local CTRL_BUTTON_NAMES = {'left ctrl', 'lctrl', 'left control'}

local CATALOG = {
    ["40 k meltagun"] = "40-K Meltagun",
    ["500 kg"] = "Eagle 500kg Bomb",
    ["500kg"] = "Eagle 500kg Bomb",
    ["a ac 8 autocannon sentry"] = "A/AC-8 Autocannon Sentry",
    ["a arc 3 tesla tower"] = "A/ARC-3 Tesla Tower",
    ["a flam 40 flame sentry"] = "A/FLAM-40 Flame Sentry",
    ["a g 16 gatling sentry"] = "A/G-16 Gatling Sentry",
    ["a gm 17 gas mortar sentry"] = "A/GM-17 Gas Mortar Sentry",
    ["a las 98 laser sentry"] = "A/LAS-98 Laser Sentry",
    ["a m 12 mortar sentry"] = "A/M-12 Mortar Sentry",
    ["a m 23 ems mortar sentry"] = "A/M-23 EMS Mortar Sentry",
    ["a mg 43 machine gun sentry"] = "A/MG-43 Machine Gun Sentry",
    ["a mls 4x rocket sentry"] = "A/MLS-4X Rocket Sentry",
    ["ac 8 autocannon"] = "AC-8 Autocannon",
    ["activate e 711 extraction drill"] = "Activate E-711 Extraction Drill",
    ["airburst rocket launcher"] = "RL-77 Airburst Rocket Launcher",
    ["anti materiel rifle"] = "APW-1 Anti-Materiel Rifle",
    ["anti personnel minefield"] = "MD-6 Anti-Personnel Minefield",
    ["anti tank emplacement"] = "E/AT-12 Anti-Tank Emplacement",
    ["anti tank mines"] = "MD-17 Anti-Tank Mines",
    ["apw 1 anti materiel rifle"] = "APW-1 Anti-Materiel Rifle",
    ["aquifer drill"] = "Aquifer Drill",
    ["arc 3 arc thrower"] = "ARC-3 Arc Thrower",
    ["arc thrower"] = "ARC-3 Arc Thrower",
    ["autocannon"] = "AC-8 Autocannon",
    ["autocannon sentry"] = "A/AC-8 Autocannon Sentry",
    ["ax ar 23 guard dog"] = "AX/AR-23 Guard Dog",
    ["ax arc 3 k 9"] = "AX/ARC-3 K-9",
    ["ax flam 75 hot dog"] = "AX/FLAM-75 Hot Dog",
    ["ax las 5 rover"] = "AX/LAS-5 Rover",
    ["ax tx 13 dog breath"] = "AX/TX-13 Dog Breath",
    ["b 1 supply pack"] = "B-1 Supply Pack",
    ["b 100 portable hellbomb"] = "B-100 Portable Hellbomb",
    ["b flam 80 cremator"] = "B/FLAM-80 Cremator",
    ["b md c4 pack"] = "B/MD C4 Pack",
    ["ballistic shield backpack"] = "SH-20 Ballistic Shield Backpack",
    ["bastion mk xvi"] = "TD-220 Bastion MK XVI",
    ["belt fed grenade launcher"] = "GL-28 Belt-Fed Grenade Launcher",
    ["breaching hammer"] = "CQC-20 Breaching Hammer",
    ["breakthrough exosuit"] = "EXO-55 Breakthrough Exosuit",
    ["bullet storm"] = "MGX-42 Bullet Storm",
    ["c4 pack"] = "B/MD C4 Pack",
    ["call in super destroyer"] = "Call In Super Destroyer",
    ["cargo container"] = "Cargo Container",
    ["commando"] = "MLS-4X Commando",
    ["cqc 1 one true flag"] = "CQC-1 One True Flag",
    ["cqc 20 breaching hammer"] = "CQC-20 Breaching Hammer",
    ["cqc 9 defoliation tool"] = "CQC-9 Defoliation Tool",
    ["cremator"] = "B/FLAM-80 Cremator",
    ["dark fluid vessel"] = "Dark Fluid Vessel",
    ["de escalator"] = "GL-52 De-Escalator",
    ["defoliation tool"] = "CQC-9 Defoliation Tool",
    ["directional shield"] = "SH-51 Directional Shield",
    ["dog breath"] = "AX/TX-13 Dog Breath",
    ["e at 12 anti tank emplacement"] = "E/AT-12 Anti-Tank Emplacement",
    ["e gl 21 grenadier battlement"] = "E/GL-21 Grenadier Battlement",
    ["e mg 101 hmg emplacement"] = "E/MG-101 HMG Emplacement",
    ["eagle 110mm rocket pods"] = "Eagle 110mm Rocket Pods",
    ["eagle 500kg bomb"] = "Eagle 500kg Bomb",
    ["eagle airstrike"] = "Eagle Airstrike",
    ["eagle cluster bomb"] = "Eagle Cluster Bomb",
    ["eagle gas airstrike"] = "Eagle Gas Airstrike",
    ["eagle napalm airstrike"] = "Eagle Napalm Airstrike",
    ["eagle rearm"] = "Eagle Rearm",
    ["eagle smoke strike"] = "Eagle Smoke Strike",
    ["eagle strafing run"] = "Eagle Strafing Run",
    ["eat 17 expendable anti tank"] = "EAT-17 Expendable Anti-Tank",
    ["eat 411 leveller"] = "EAT-411 Leveller",
    ["eat 700 expendable napalm"] = "EAT-700 Expendable Napalm",
    ["emancipator exosuit"] = "EXO-49 Emancipator Exosuit",
    ["ems mortar sentry"] = "A/M-23 EMS Mortar Sentry",
    ["epoch"] = "PLAS-45 Epoch",
    ["exo 45 patriot exosuit"] = "EXO-45 Patriot Exosuit",
    ["exo 49 emancipator exosuit"] = "EXO-49 Emancipator Exosuit",
    ["exo 51 lumberer exosuit"] = "EXO-51 Lumberer Exosuit",
    ["exo 55 breakthrough exosuit"] = "EXO-55 Breakthrough Exosuit",
    ["expendable anti tank"] = "EAT-17 Expendable Anti-Tank",
    ["expendable napalm"] = "EAT-700 Expendable Napalm",
    ["faf 14 spear"] = "FAF-14 Spear",
    ["flam 40 flamethrower"] = "FLAM-40 Flamethrower",
    ["flame sentry"] = "A/FLAM-40 Flame Sentry",
    ["flamethrower"] = "FLAM-40 Flamethrower",
    ["fx 12 shield generator relay"] = "FX-12 Shield Generator Relay",
    ["gas mines"] = "MD-8 Gas Mines",
    ["gas mortar sentry"] = "A/GM-17 Gas Mortar Sentry",
    ["gatling sentry"] = "A/G-16 Gatling Sentry",
    ["gl 21 grenade launcher"] = "GL-21 Grenade Launcher",
    ["gl 28 belt fed grenade launcher"] = "GL-28 Belt-Fed Grenade Launcher",
    ["gl 52 de escalator"] = "GL-52 De-Escalator",
    ["gr 8 recoilless rifle"] = "GR-8 Recoilless Rifle",
    ["grenade launcher"] = "GL-21 Grenade Launcher",
    ["grenadier battlement"] = "E/GL-21 Grenadier Battlement",
    ["guard dog"] = "AX/AR-23 Guard Dog",
    ["gunner frv"] = "M-102 Gunner FRV",
    ["heavy machine gun"] = "MG-206 Heavy Machine Gun",
    ["hellbomb"] = "NUX-223 Hellbomb",
    ["hive breaker drill"] = "Hive Breaker Drill",
    ["hmg emplacement"] = "E/MG-101 HMG Emplacement",
    ["hot dog"] = "AX/FLAM-75 Hot Dog",
    ["hover pack"] = "LIFT-860 Hover Pack",
    ["incendiary mines"] = "MD-I4 Incendiary Mines",
    ["incinerator frv"] = "M-104 Incinerator FRV",
    ["jump pack"] = "LIFT-850 Jump Pack",
    ["k 9"] = "AX/ARC-3 K-9",
    ["las 98 laser cannon"] = "LAS-98 Laser Cannon",
    ["las 99 quasar cannon"] = "LAS-99 Quasar Cannon",
    ["laser cannon"] = "LAS-98 Laser Cannon",
    ["laser sentry"] = "A/LAS-98 Laser Sentry",
    ["leveller"] = "EAT-411 Leveller",
    ["lift 182 warp pack"] = "LIFT-182 Warp Pack",
    ["lift 850 jump pack"] = "LIFT-850 Jump Pack",
    ["lift 860 hover pack"] = "LIFT-860 Hover Pack",
    ["lumberer exosuit"] = "EXO-51 Lumberer Exosuit",
    ["m 1000 maxigun"] = "M-1000 Maxigun",
    ["m 102 gunner frv"] = "M-102 Gunner FRV",
    ["m 103 supply frv"] = "M-103 Supply FRV",
    ["m 104 incinerator frv"] = "M-104 Incinerator FRV",
    ["m 105 stalwart"] = "M-105 Stalwart",
    ["machine gun"] = "MG-43 Machine Gun",
    ["machine gun sentry"] = "A/MG-43 Machine Gun Sentry",
    ["maelstrom"] = "TD-110 Maelstrom",
    ["maxigun"] = "M-1000 Maxigun",
    ["md 17 anti tank mines"] = "MD-17 Anti-Tank Mines",
    ["md 6 anti personnel minefield"] = "MD-6 Anti-Personnel Minefield",
    ["md 8 gas mines"] = "MD-8 Gas Mines",
    ["md i4 incendiary mines"] = "MD-I4 Incendiary Mines",
    ["meltagun"] = "40-K Meltagun",
    ["mg 206 heavy machine gun"] = "MG-206 Heavy Machine Gun",
    ["mg 43 machine gun"] = "MG-43 Machine Gun",
    ["mgx 42 bullet storm"] = "MGX-42 Bullet Storm",
    ["mls 4x commando"] = "MLS-4X Commando",
    ["mortar sentry"] = "A/M-12 Mortar Sentry",
    ["ms 11 solo silo"] = "MS-11 Solo Silo",
    ["nux 223 hellbomb"] = "NUX-223 Hellbomb",
    ["one true flag"] = "CQC-1 One True Flag",
    ["orbital 120mm he barrage"] = "Orbital 120mm HE Barrage",
    ["orbital 380mm he barrage"] = "Orbital 380mm HE Barrage",
    ["orbital airburst strike"] = "Orbital Airburst Strike",
    ["orbital ems strike"] = "Orbital EMS Strike",
    ["orbital gas strike"] = "Orbital Gas Strike",
    ["orbital gatling barrage"] = "Orbital Gatling Barrage",
    ["orbital illumination flare"] = "Orbital Illumination Flare",
    ["orbital laser"] = "Orbital Laser",
    ["orbital napalm barrage"] = "Orbital Napalm Barrage",
    ["orbital precision strike"] = "Orbital Precision Strike",
    ["orbital railcannon strike"] = "Orbital Railcannon Strike",
    ["orbital smoke strike"] = "Orbital Smoke Strike",
    ["orbital walking barrage"] = "Orbital Walking Barrage",
    ["patriot exosuit"] = "EXO-45 Patriot Exosuit",
    ["plas 45 epoch"] = "PLAS-45 Epoch",
    ["portable comms relay"] = "Portable Comms Relay",
    ["portable hellbomb"] = "B-100 Portable Hellbomb",
    ["precision strike"] = "Orbital Precision Strike",
    ["prospecting drill"] = "Prospecting Drill",
    ["quasar cannon"] = "LAS-99 Quasar Cannon",
    ["railgun"] = "RS-422 Railgun",
    ["recoilless rifle"] = "GR-8 Recoilless Rifle",
    ["reinforce"] = "Reinforce",
    ["reinforcement pods"] = "Reinforcement Pods",
    ["resupply"] = "Resupply",
    ["rl 77 airburst rocket launcher"] = "RL-77 Airburst Rocket Launcher",
    ["rocket sentry"] = "A/MLS-4X Rocket Sentry",
    ["rover"] = "AX/LAS-5 Rover",
    ["rs 422 railgun"] = "RS-422 Railgun",
    ["s 11 speargun"] = "S-11 Speargun",
    ["seaf artillery"] = "SEAF Artillery",
    ["seismic probe"] = "Seismic Probe",
    ["sh 20 ballistic shield backpack"] = "SH-20 Ballistic Shield Backpack",
    ["sh 32 shield generator pack"] = "SH-32 Shield Generator Pack",
    ["sh 51 directional shield"] = "SH-51 Directional Shield",
    ["shield generator pack"] = "SH-32 Shield Generator Pack",
    ["shield generator relay"] = "FX-12 Shield Generator Relay",
    ["solo silo"] = "MS-11 Solo Silo",
    ["sos"] = "SoS Beacon",
    ["sos beacon"] = "SoS Beacon",
    ["spear"] = "FAF-14 Spear",
    ["speargun"] = "S-11 Speargun",
    ["sssd delivery"] = "SSSD Delivery",
    ["sta x3 wasp launcher"] = "StA-X3 W.A.S.P. Launcher",
    ["stalwart"] = "M-105 Stalwart",
    ["sterilizer"] = "TX-41 Sterilizer",
    ["super earth flag"] = "Super Earth Flag",
    ["supply frv"] = "M-103 Supply FRV",
    ["supply pack"] = "B-1 Supply Pack",
    ["tactical video camera"] = "Tactical Video Camera",
    ["td 110 maelstrom"] = "TD-110 Maelstrom",
    ["td 220 bastion mk xvi"] = "TD-220 Bastion MK XVI",
    ["tectonic drill"] = "Tectonic Drill",
    ["tesla tower"] = "A/ARC-3 Tesla Tower",
    ["tx 41 sterilizer"] = "TX-41 Sterilizer",
    ["upload data"] = "Upload Data",
    ["warp pack"] = "LIFT-182 Warp Pack",
    ["wasp launcher"] = "StA-X3 W.A.S.P. Launcher",
}

local api = {api = 1, mod = 'EquippedStratagems', names = nil}
local last_body = nil
local have_names = false
local elapsed = POLL_SECONDS
local binding_registered = false
local binding_down = false
local menu_down = false
local cached_owner = nil
local cached_actions = nil

local function fold(value)
    local folded = value:lower()
    folded = folded:gsub('w%.a%.s%.p%.', 'wasp')
    folded = folded:gsub('s%.o%.s%.', 'sos')
    folded = folded:gsub('s%.o%.s', 'sos')
    folded = folded:gsub('[^a-z0-9]+', ' ')
    return (folded:gsub('^ +', ''):gsub(' +$', ''):gsub(' +', ' '))
end

function api.catalog_name(text)
    if type(text) ~= 'string' then return nil end
    return CATALOG[fold(text)]
end

local function trim(value)
    return (value:gsub('^%s+', ''):gsub('%s+$', ''))
end

local function as_name_list(value)
    if type(value) ~= 'table' then return nil end
    local count = #value
    if count == 0 then
        if next(value) ~= nil then return nil end
        return {}
    end
    local names = {}
    for index = 1, count do
        local item = value[index]
        if type(item) ~= 'string' or item:find('\n', 1, true) then return nil end
        local name = trim(item)
        if name == '' then return nil end
        names[index] = name
    end
    return names
end

local function canonical(raw)
    if not raw then return nil end
    if #raw == 0 then return {} end
    local names, seen = {}, {}
    for index = 1, #raw do
        local name = CATALOG[fold(raw[index])]
        if name and not seen[name] then
            seen[name] = true
            names[#names + 1] = name
        end
    end
    if #names == 0 then return nil end
    return names
end

local function u32(bytes, offset)
    if type(bytes) ~= 'string' or offset < 0 or offset + 4 > #bytes then return nil end
    local a, b, c, d = bytes:byte(offset + 1, offset + 4)
    if not d then return nil end
    return a + b * 256 + c * 65536 + d * 16777216
end

local function best_catalog_name(blob)
    if type(blob) ~= 'string' or blob == '' then return nil end
    local best_name, best_len = nil, 3
    local index = 1
    while index <= #blob do
        local byte = blob:byte(index)
        if byte >= 32 and byte < 127 then
            local finish = index
            while finish <= #blob do
                local next_byte = blob:byte(finish)
                if next_byte < 32 or next_byte >= 127 then break end
                finish = finish + 1
            end
            local word = blob:sub(index, finish - 1)
            local name = CATALOG[fold(word)]
            if name and #word > best_len then
                best_name, best_len = name, #word
            end
            index = finish + 1
        else
            index = index + 1
        end
    end
    return best_name
end

local function address_add(base, offset)
    return base + offset
end

local function address_distance(address, base)
    if type(address) == 'number' and type(base) == 'number' then
        return address - base
    end
    local ok, ffi = pcall(require, 'ffi')
    if not ok or type(ffi) ~= 'table' or type(ffi.cast) ~= 'function' then return nil end
    return tonumber(ffi.cast('intptr_t', address) - ffi.cast('intptr_t', base))
end

-- The compiled loadouts patch does not return a name array. Report only
-- whether package.loaded already holds one catalog list.
local function loadouts_usable()
    local loaded = package and package.loaded
    local module = type(loaded) == 'table' and loaded[LOADOUTS_MODULE] or nil
    if type(module) ~= 'table' then return false end
    local list = as_name_list(module)
    if not list or #list == 0 then return false end
    local names = canonical(list)
    return names ~= nil and #names > 0 and #names <= MAX_EQUIPPED
end

local function usable_address(value)
    return type(value) == 'number' and value >= 0x10000 and value < 0x800000000000
end

local function windows_reader()
    local injected = rawget(_G, 'EquippedStratagemsReader')
    if type(injected) == 'table' then return injected end
    local ok, ffi = pcall(require, 'ffi')
    if not ok or type(ffi) ~= 'table' or type(ffi.abi) ~= 'function' or not ffi.abi('64bit') then
        return nil
    end
    pcall(ffi.cdef, [[
        void *GetModuleHandleA(const char *name);
        void *GetCurrentProcess(void);
        int ReadProcessMemory(void *process, const void *address, void *buffer, size_t size, size_t *read);
        unsigned short GetAsyncKeyState(int key);
    ]])
    local kernel = ffi.load('kernel32')
    local user32_ok, user32 = pcall(ffi.load, 'user32')
    local process = kernel.GetCurrentProcess()
    local api = {}
    function api.module(name)
        local handle = kernel.GetModuleHandleA(name)
        if handle == nil then return nil end
        local base = tonumber(ffi.cast('uintptr_t', handle))
        if not usable_address(base) then return nil end
        return base
    end
    function api.read(address, size)
        if not usable_address(address) or type(size) ~= 'number' then return nil end
        if size < 1 or size > 131072 or size % 1 ~= 0 then return nil end
        local buffer, count = ffi.new('uint8_t[?]', size), ffi.new('size_t[1]')
        if kernel.ReadProcessMemory(process, ffi.cast('const void *', address), buffer, size, count) == 0
            or tonumber(count[0]) ~= size then
            return nil
        end
        return ffi.string(buffer, size)
    end
    function api.pointer(bytes, offset)
        offset = offset or 0
        if type(bytes) ~= 'string' or offset < 0 or offset + 8 > #bytes then return nil end
        local value = ffi.new('uintptr_t[1]')
        ffi.copy(value, bytes:sub(offset + 1, offset + 8), 8)
        local address = tonumber(value[0])
        if not usable_address(address) then return nil end
        return address
    end
    function api.key_down(vk)
        if not user32_ok or type(vk) ~= 'number' then return false end
        local value = tonumber(user32.GetAsyncKeyState(vk))
        if not value then return false end
        if value < 0 then value = value + 65536 end
        return value >= 0x8000
    end
    return api
end

-- StratagemInfo display names, keyed by kind. Same group walk as
-- BetterStratagemBounce navigation_patch.prepare, read-only.
local function stratagem_names(api, game)
    local buffer = api.pointer(api.read(game + SETTINGS_RVA, 8))
    if not buffer then return nil end
    local source = api.read(buffer, SETTINGS_SIZE)
    if type(source) ~= 'string' or #source ~= SETTINGS_SIZE or u32(source, 0) ~= 11 then return nil end
    local table_bytes = api.read(game + TABLE_RVA, 150 * 8)
    if type(table_bytes) ~= 'string' or #table_bytes ~= 150 * 8 then return nil end
    local offset, names, seen, records, by_address = 4, {}, {}, 0, {}
    for _ = 1, 11 do
        if u32(source, offset) ~= 0x444C444C or u32(source, offset + 4) ~= 1
            or u32(source, offset + 8) ~= 0x30EB6399
            or u32(source, offset + 16) ~= 1 or u32(source, offset + 20) ~= 0 then
            return nil
        end
        local root = offset + 24
        local finish = root + u32(source, offset + 12)
        if finish < root + 16 or finish > #source then return nil end
        local count = u32(source, root + 8)
        if not count or count < 1 or count > 149 then return nil end
        local items = api.pointer(source, root)
        local start = items and address_distance(items, buffer)
        if not start or start < root + 16 or start + count * RECORD_SIZE > finish then return nil end
        for index = 0, count - 1 do
            local record = start + index * RECORD_SIZE
            local kind = u32(source, record)
            if not kind or kind < 1 or kind > 149 or seen[kind] then return nil end
            local pointed = api.pointer(table_bytes, kind * 8)
            if pointed ~= address_add(buffer, record) then return nil end
            seen[kind], records = true, records + 1
            by_address[address_add(buffer, record)] = kind
            local record_bytes = source:sub(record + 1, record + RECORD_SIZE)
            local name = best_catalog_name(record_bytes:sub(5))
            if not name then
                local tries = 0
                for slot = 0, RECORD_SIZE - 8, 8 do
                    local address = api.pointer(record_bytes, slot)
                    if usable_address(address) then
                        tries = tries + 1
                        if tries > 4 then break end
                        local text = api.read(address, 96)
                        name = type(text) == 'string' and best_catalog_name(text) or nil
                        if name then break end
                    end
                end
            end
            names[kind] = name
        end
        offset = finish
    end
    if offset ~= #source or records ~= 149 then return nil end
    return names, by_address
end

-- Mission type 1..7, same gate as ShallowWaterDiving and spawn_data.
-- 0 means the ship menu. nil means the mode block is not readable yet.
local function mission_type(api, game)
    local mode = api.pointer(api.read(game + MISSION_RVA, 8))
    if not usable_address(mode) then return nil end
    local bytes = api.read(mode, 0x44)
    if type(bytes) ~= 'string' or #bytes ~= 0x44 then return nil end
    if u32(bytes, 8) == 0 then return 0 end
    return u32(bytes, 0x40)
end

local function dedupe_names(raw)
    local names, seen = {}, {}
    for index = 1, #raw do
        local name = raw[index]
        if name and not seen[name] then
            seen[name] = true
            names[#names + 1] = name
        end
    end
    if #names == 0 then return nil end
    return names
end

local function names_from_kinds(packed, count, by_kind)
    local raw = {}
    for index = 0, count - 1 do
        local kind = u32(packed, index * 4)
        local name = kind and by_kind[kind]
        if not name then return nil end
        raw[#raw + 1] = name
    end
    return dedupe_names(raw)
end

local function names_from_records(packed, count, by_address, by_kind, reader)
    local raw = {}
    for index = 0, count - 1 do
        local address = reader.pointer(packed, index * 8)
        local kind = address and by_address[address]
        local name = kind and by_kind[kind]
        if not name then return nil end
        raw[#raw + 1] = name
    end
    return dedupe_names(raw)
end

local function prefer(best, priority, names, count)
    if not names or not count or count < MIN_LOADOUT then return best end
    if not best or priority > best.priority or (priority == best.priority and count > best.count) then
        return {priority = priority, names = names, count = count}
    end
    return best
end

-- Stingray array inside the player block: count, capacity, data pointer.
-- Record pointers win over packed kind ids. The empty inline field at
-- EMPTY_SLOT_OFFSET is never the start of this array.
local function arrays_in_span(reader, bytes, start_at, finish, by_kind, by_address, best)
    local offset = start_at
    while offset + 16 <= finish do
        if offset ~= EMPTY_SLOT_OFFSET then
            local count = u32(bytes, offset)
            local capacity = u32(bytes, offset + 4)
            local data = reader.pointer(bytes, offset + 8)
            if count and capacity and data and count >= MIN_LOADOUT and count <= MAX_EQUIPPED
                and capacity >= count and capacity <= MAX_CAPACITY then
                local pointers = reader.read(data, count * 8)
                if type(pointers) == 'string' and #pointers == count * 8 then
                    best = prefer(best, 3, names_from_records(pointers, count, by_address, by_kind, reader), count)
                end
                local packed = reader.read(data, count * 4)
                if type(packed) == 'string' and #packed == count * 4 then
                    best = prefer(best, 2, names_from_kinds(packed, count, by_kind), count)
                end
            end
        end
        offset = offset + 8
    end
    return best
end

-- Inline catalog kinds, terminated by 0 or 0xFFFFFFFF. The empty field is a
-- hard gap so a zero there cannot end the list before the real slots.
local function inline_in_span(bytes, start_at, finish, by_kind, best)
    local offset = start_at
    while offset + 12 <= finish do
        if offset == EMPTY_SLOT_OFFSET then
            offset = offset + 4
        else
            local raw, at = {}, offset
            while at + 4 <= finish and at ~= EMPTY_SLOT_OFFSET do
                local kind = u32(bytes, at)
                if not kind or kind == 0 or kind == 0xFFFFFFFF then break end
                local name = by_kind[kind]
                if not name then break end
                raw[#raw + 1] = name
                at = at + 4
            end
            local ended = at ~= offset and (at == EMPTY_SLOT_OFFSET or at + 4 > finish
                or u32(bytes, at) == 0 or u32(bytes, at) == 0xFFFFFFFF)
            if ended and #raw >= 3 then
                best = prefer(best, 1, dedupe_names(raw), #raw)
            end
            if at > offset then offset = at else offset = offset + 4 end
        end
    end
    return best
end

local function equipped_slots(reader, player, by_kind, by_address)
    local best = nil
    for index = 1, #ARRAY_SPANS do
        local span = ARRAY_SPANS[index]
        best = arrays_in_span(reader, player, span[1], span[2], by_kind, by_address, best)
        best = inline_in_span(player, span[1], span[2], by_kind, best)
    end
    if not best then return nil, nil end
    return best.names, best.count
end

local function ctrl_button_ids()
    local engine = rawget(_G, 'stingray')
    local keyboard = type(engine) == 'table' and engine.Keyboard or nil
    local button_id = type(keyboard) == 'table' and keyboard.button_id or nil
    if type(button_id) ~= 'function' then return nil end
    local ids = {}
    for _, name in ipairs(CTRL_BUTTON_NAMES) do
        local ok, id = pcall(button_id, name)
        local numeric = ok and tonumber(id) or nil
        if numeric and numeric >= 0 and numeric <= 255 and numeric % 1 == 0 then
            ids[numeric] = true
        end
    end
    if next(ids) == nil then return nil end
    return ids
end

local function fallback_ctrl(reader)
    if type(reader) ~= 'table' or type(reader.key_down) ~= 'function' then return false end
    for _, vk in ipairs({VK_LCONTROL, VK_RCONTROL, VK_CONTROL}) do
        local ok, down = pcall(reader.key_down, vk)
        if ok and down then return true end
    end
    return false
end

-- Returns the input owner and the actions whose shipped keyboard default is
-- Left Ctrl. Hold actions are preferred. nil actions means the defaults map
-- was readable but Left Ctrl was not on it.
local function menu_actions(reader, game)
    local ids = ctrl_button_ids()
    if not ids then return nil, nil end
    local owner = reader.pointer(reader.read(game + INPUT_OWNER_RVA, 8))
    if not usable_address(owner) then return nil, nil end
    if cached_actions and cached_owner == owner then return owner, cached_actions end
    local capacity = u32(reader.read(owner + DEFAULTS_MAP + 8, 4) or '', 0)
    if capacity ~= 256 then return nil, nil end
    local map = reader.pointer(reader.read(owner + DEFAULTS_MAP, 8))
    if not usable_address(map) then return nil, nil end
    local blob = reader.read(map, 256 * BINDING_RECORD)
    if type(blob) ~= 'string' or #blob ~= 256 * BINDING_RECORD then return nil, nil end
    local hold, other = {}, {}
    for index = 0, 255 do
        local base = index * BINDING_RECORD
        local code = u32(blob, base)
        local count = u32(blob, base + 4)
        if code and count and count > 0 and count <= 16 then
            local group = math.floor(code / 65536)
            local action = code % 65536
            if group < 64 and action < 97 then
                for mapping_index = 0, count - 1 do
                    local at = base + 8 + mapping_index * MAPPING_SIZE
                    local first = blob:byte(at + 1)
                    local key = blob:byte(at + 5)
                    if first and key and first % 16 == KEYBOARD_DEVICE
                        and math.floor(first / 16) % 16 == BUTTON_INPUT and ids[key] then
                        local entry = {group = group, action = action}
                        if u32(blob, at + 8) == HOLD_TRIGGER then
                            hold[#hold + 1] = entry
                        else
                            other[#other + 1] = entry
                        end
                    end
                end
            end
        end
    end
    local chosen = #hold > 0 and hold or (#other > 0 and other or nil)
    if not chosen then return owner, nil end
    cached_owner, cached_actions = owner, chosen
    return owner, chosen
end

local function action_down(reader, owner, entry)
    local index = entry.group * 97 + entry.action
    local byte = reader.read(owner + ACTION_STATE_OFFSET + ACTION_STATE_STRIDE * index, 1)
    return type(byte) == 'string' and byte ~= '\0'
end

local function stratagem_menu_open(reader, game)
    local owner, actions = menu_actions(reader, game)
    if actions then
        for _, entry in ipairs(actions) do
            if action_down(reader, owner, entry) then return true end
        end
        return false
    end
    return fallback_ctrl(reader)
end

local function probe_equipped()
    local probe = {loadouts = loadouts_usable(), game = false, menu = false, count = nil, names = nil}
    pcall(function()
        local reader = windows_reader()
        if type(reader) ~= 'table' or type(reader.module) ~= 'function' then return end
        local game = reader.module('game.dll')
        if not usable_address(game) then return end
        probe.game = true
        probe.menu = stratagem_menu_open(reader, game)
        local mission = mission_type(reader, game)
        local player = reader.pointer(reader.read(game + PLAYER_RVA, 8))
        if not usable_address(player) then return end
        local bytes = reader.read(player, 0x440)
        if type(bytes) ~= 'string' or #bytes ~= 0x440 then return end
        local by_kind, by_address = stratagem_names(reader, game)
        local names, count = equipped_slots(reader, bytes, by_kind or {}, by_address or {})
        probe.count = count
        -- Ship menu slots are not the mission loadout. A count of zero is
        -- not a loadout either: empty +0x1D0 must not be the only line once
        -- this menu is open in a mission.
        if not mission or mission < 1 or mission > 7 then return end
        if not names or not count or count < MIN_LOADOUT then return end
        probe.names = names
    end)
    return probe
end

local function write_body(body)
    if body == last_body then return end
    local loader = rawget(_G, 'CowboyBingusModLoader')
    local open_log = loader and loader.open_log
    if type(open_log) ~= 'function' then return end
    local ok, file = pcall(open_log, LOG_NAME)
    if not ok or not file then return end
    local wrote = pcall(function()
        file:write(body)
        if body ~= '' and body:sub(-1) ~= '\n' then file:write('\n') end
        file:close()
    end)
    if wrote then last_body = body end
end

local function write_names(names, count)
    have_names = true
    local body = table.concat(names, '\n')
    if count and count >= MIN_LOADOUT then
        body = body .. '\n# count=' .. tostring(count)
    end
    write_body(body)
end

local function write_status(probe)
    if have_names then return end
    local count = probe.count == nil and 'unread' or tostring(probe.count)
    write_body('# loadouts=' .. (probe.loadouts and 'yes' or 'no')
        .. '\n# game.dll=' .. (probe.game and 'yes' or 'no')
        .. '\n# menu=' .. (probe.menu and 'open' or 'closed')
        .. '\n# count=' .. count)
end

local function flush_loadout(allow_names)
    local probe = probe_equipped()
    local names = allow_names and probe.names and canonical(probe.names) or nil
    if names and #names > 0 and probe.count and probe.count >= MIN_LOADOUT then
        api.names = names
        write_names(names, probe.count)
    else
        write_status(probe)
    end
end

local function publish_list(raw)
    local list = as_name_list(raw)
    if not list then return nil end
    return canonical(list)
end

function api.publish(names)
    local list = publish_list(names)
    if not list then return false end
    api.names = list
    write_names(list)
    return true
end

local function service_binding()
    local menu = rawget(_G, 'ModBindingsMenu')
    if type(menu) ~= 'table' or menu.api ~= 1 or type(menu.register_binding) ~= 'function' then return end
    if not binding_registered then
        local called, ok = pcall(menu.register_binding, BINDING_ID, BINDING_LABEL, nil, {category = 'EquippedStratagems'})
        if not called or not ok then return end
        binding_registered = true
    end
    if type(menu.is_down) ~= 'function' then return end
    local called, down = pcall(menu.is_down, BINDING_ID)
    if not called or down == nil then return end
    if down and not binding_down then
        flush_loadout(true)
    end
    binding_down = down
end

local function menu_is_open()
    local open = false
    pcall(function()
        local reader = windows_reader()
        if type(reader) ~= 'table' or type(reader.module) ~= 'function' then return end
        local game = reader.module('game.dll')
        if not usable_address(game) then return end
        open = stratagem_menu_open(reader, game)
    end)
    return open
end

local function service_menu()
    local open = menu_is_open()
    if open and not menu_down then
        flush_loadout(true)
    end
    menu_down = open
end

rawset(_G, 'EquippedStratagems', api)

local previous_update = rawget(_G, 'update')
update = function(dt, ...)
    service_menu()
    service_binding()
    elapsed = elapsed + (type(dt) == 'number' and dt or 0)
    if elapsed >= POLL_SECONDS then
        elapsed = 0
        flush_loadout(menu_down)
    end
    if type(previous_update) == 'function' then return previous_update(dt, ...) end
end

print('[EquippedStratagems] loaded')
