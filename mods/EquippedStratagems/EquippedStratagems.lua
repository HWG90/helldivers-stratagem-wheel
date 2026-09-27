-- HD2-Addon: mods/EquippedStratagems/EquippedStratagems

-- Writes equipped stratagems, one catalog name per line, for the stratagem wheel.
-- Bingus Shared Loader discovers this entry, opens the log, and chains update.
-- The equipped list is read from the game's script/lua/player module.
-- Send Strategems is a Mod Bindings Menu binding. This file does not scan
-- memory, patch code, or hide itself.

local prior = rawget(_G, 'EquippedStratagems')
if type(prior) == 'table' and prior.mod == 'EquippedStratagems' then return end

local LOG_NAME = 'EquippedStratagems.log'
local RESOURCE = 'mods/EquippedStratagems/EquippedStratagems'
local BINDING_ID = 'equippedstratagems.send_strategems'
local BINDING_LABEL = 'Send Strategems'
local GAME_SCRIPTS = {'script/lua/player', 'script/lua/player_hud'}
local NESTED_KEYS = {'loadout', 'stratagems', 'slots', 'player', 'hud', 'equipment'}
local POLL_SECONDS = 0.5
local FUNCTION_NAMES = {'equipped', 'loadout', 'slots', 'names', 'get_loadout', 'equipped_stratagems', 'current'}
local SETTING_KEYS = {'equipped_stratagems', 'stratagem_loadout', 'stratagems', 'loadout'}
local GLOBAL_KEYS = {'StratagemLoadout', 'PlayerLoadout'}

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
local elapsed = POLL_SECONDS
local binding_registered = false
local binding_down = false

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

local function call_list(fn)
    if type(fn) ~= 'function' then return nil end
    local ok, value = pcall(fn)
    if not ok then return nil end
    return as_name_list(value)
end

local function from_module(module)
    local direct = as_name_list(module)
    if direct then return direct end
    if type(module) ~= 'table' then return nil end
    for _, field in ipairs(FUNCTION_NAMES) do
        local value = module[field]
        local names = as_name_list(value) or call_list(value)
        if names then return names end
    end
    return nil
end

local function from_loaded_modules()
    local loaded = package and package.loaded
    if type(loaded) ~= 'table' then return nil end
    local keys = {}
    for key in pairs(loaded) do
        if type(key) == 'string' then keys[#keys + 1] = key end
    end
    table.sort(keys)
    for _, key in ipairs(keys) do
        local folded = key:lower()
        if key ~= RESOURCE and (folded:find('stratagem', 1, true) or folded:find('loadout', 1, true)) then
            local names = from_module(loaded[key])
            if names then return names end
        end
    end
    return nil
end

local function from_user_settings()
    local engine = rawget(_G, 'stingray')
    local app = engine and engine.Application
    if not app or type(app.user_setting) ~= 'function' then return nil end
    for _, key in ipairs(SETTING_KEYS) do
        local ok, value = pcall(app.user_setting, key)
        if ok then
            local names = as_name_list(value)
            if names then return names end
        end
    end
    return nil
end

local function from_globals()
    for _, key in ipairs(GLOBAL_KEYS) do
        local names = as_name_list(rawget(_G, key))
        if names then return names end
    end
    return nil
end

local function load_game_script(name)
    local loaded = package and package.loaded and package.loaded[name]
    if type(loaded) == 'table' then return loaded end
    local engine = rawget(_G, 'stingray')
    local app = engine and engine.Application
    if not app or type(app.can_get) ~= 'function' then return nil end
    local ok, available = pcall(app.can_get, 'lua', name)
    if not ok or not available then return nil end
    local required, module = pcall(require, name)
    if required and type(module) == 'table' then return module end
    loaded = package and package.loaded and package.loaded[name]
    if type(loaded) == 'table' then return loaded end
    return nil
end

local function from_record(module)
    local names = from_module(module)
    if names then return names end
    if type(module) ~= 'table' then return nil end
    for _, key in ipairs(NESTED_KEYS) do
        names = from_module(module[key])
        if names then return names end
    end
    return nil
end

-- script/lua/player is the game module. Require it the same way the loader
-- requires a lua resource: can_get, then require. Do not wait for publish.
local function read_equipped()
    for _, name in ipairs(GAME_SCRIPTS) do
        local names = from_record(load_game_script(name))
        if names then return names end
    end
    return from_globals() or from_user_settings() or from_loaded_modules()
end

local function write_names(names)
    local body = table.concat(names, '\n')
    if body == last_body then return end
    local loader = rawget(_G, 'CowboyBingusModLoader')
    local open_log = loader and loader.open_log
    if type(open_log) ~= 'function' then return end
    local ok, file = pcall(open_log, LOG_NAME)
    if not ok or not file then return end
    local wrote = pcall(function()
        if body ~= '' then file:write(body, '\n') end
        file:close()
    end)
    if wrote then last_body = body end
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
        local names = canonical(read_equipped())
        if names then write_names(names) end
    end
    binding_down = down
end

rawset(_G, 'EquippedStratagems', api)

local previous_update = rawget(_G, 'update')
update = function(dt, ...)
    service_binding()
    elapsed = elapsed + (type(dt) == 'number' and dt or 0)
    if elapsed >= POLL_SECONDS then
        elapsed = 0
        local names = canonical(read_equipped())
        if names then write_names(names) end
    end
    if type(previous_update) == 'function' then return previous_update(dt, ...) end
end

print('[EquippedStratagems] loaded')
