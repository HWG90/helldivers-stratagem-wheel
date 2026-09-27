-- HD2-Addon: mods/EquippedStratagems/EquippedStratagems
-- Exports the local player's selected and mission-granted stratagems, one name per line.
local prior = rawget(_G, 'EquippedStratagems')
if type(prior) == 'table' and prior.mod == 'EquippedStratagems' then return end
local LOG_NAME = 'EquippedStratagems.log'
local TABLE_RVA, MISSION_RVA = 0x37cb600, 0x33266a0
local BINDING_ID, BINDING_LABEL = 'equippedstratagems.send_strategems', 'Send Strategems'
local POLL_SECONDS, MAX_EQUIPPED = 0.5, 32
local api = {api=1, mod='EquippedStratagems', revision=9, names=nil}
local elapsed, binding_registered, binding_down = POLL_SECONDS, false, false
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

local function u32(bytes, offset)
    if type(bytes) ~= 'string' or offset < 0 or offset + 4 > #bytes then return nil end
    local a, b, c, d = bytes:byte(offset + 1, offset + 4)
    if not d then return nil end
    return a + b * 256 + c * 65536 + d * 16777216
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
        uint64_t GetTickCount64(void);
    ]])
    local kernel = ffi.load('kernel32')
    local process = kernel.GetCurrentProcess()
    local api = {}
    function api.clock() return tonumber(kernel.GetTickCount64()) / 1000 end
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
    return api
end

-- Direction IDs verified against live StratagemInfo definitions:
-- 1=up, 2=right, 3=down, 4=left. Names/codes from the wheel catalog.
local CODE_NAMES = {
    ["113323"] = "Cargo Container",
    ["11334242"] = "Call In Super Destroyer",
    ["1133443"] = "Portable Comms Relay",
    ["11412"] = "Eagle Rearm",
    ["114233"] = "Seismic Probe",
    ["1213"] = "Eagle Smoke Strike",
    ["1214"] = "Eagle 110mm Rocket Pods",
    ["122"] = "Eagle Strafing Run",
    ["1231"] = "Eagle Napalm Airstrike",
    ["1232"] = "Eagle Airstrike",
    ["12332"] = "Eagle Cluster Bomb",
    ["12333"] = "Eagle 500kg Bomb",
    ["1242"] = "Eagle Gas Airstrike",
    ["131313"] = "Tectonic Drill",
    ["1321"] = "SoS Beacon",
    ["13241"] = "Reinforce",
    ["142311"] = "Dark Fluid Vessel",
    ["2113"] = "SEAF Artillery",
    ["21332"] = "Orbital Railcannon Strike",
    ["221"] = "Orbital Precision Strike",
    ["222"] = "Orbital Airburst Strike",
    ["2231"] = "Orbital Smoke Strike",
    ["2232"] = "Orbital Gas Strike",
    ["223421"] = "Orbital Napalm Barrage",
    ["223423"] = "Orbital 120mm HE Barrage",
    ["2243"] = "Orbital EMS Strike",
    ["2244"] = "Orbital Illumination Flare",
    ["2311433"] = "Orbital 380mm HE Barrage",
    ["23123"] = "Orbital Laser",
    ["232323"] = "Orbital Walking Barrage",
    ["2331441"] = "Tactical Video Camera",
    ["23411"] = "Orbital Gatling Barrage",
    ["31131"] = "LIFT-850 Jump Pack",
    ["311342"] = "LIFT-860 Hover Pack",
    ["31142"] = "RL-77 Airburst Rocket Launcher",
    ["312141"] = "A/AC-8 Autocannon Sentry",
    ["312142"] = "A/ARC-3 Tesla Tower",
    ["31221"] = "A/MG-43 Machine Gun Sentry",
    ["31223"] = "A/M-12 Mortar Sentry",
    ["31224"] = "A/MLS-4X Rocket Sentry",
    ["312311"] = "A/FLAM-40 Flame Sentry",
    ["312312"] = "A/LAS-98 Laser Sentry",
    ["31232"] = "A/M-23 EMS Mortar Sentry",
    ["31233"] = "MS-11 Solo Silo",
    ["31234"] = "A/GM-17 Gas Mortar Sentry",
    ["3124"] = "A/G-16 Gatling Sentry",
    ["3131"] = "Super Earth Flag",
    ["314121"] = "AX/TX-13 Dog Breath",
    ["314122"] = "AX/LAS-5 Rover",
    ["314123"] = "AX/AR-23 Guard Dog",
    ["314124"] = "AX/ARC-3 K-9",
    ["314144"] = "AX/FLAM-75 Hot Dog",
    ["314211"] = "SH-51 Directional Shield",
    ["314222"] = "E/AT-12 Anti-Tank Emplacement",
    ["314224"] = "E/MG-101 HMG Emplacement",
    ["314242"] = "SH-32 Shield Generator Pack",
    ["31431231"] = "NUX-223 Hellbomb",
    ["32111"] = "B-100 Portable Hellbomb",
    ["321121"] = "B/MD C4 Pack",
    ["32142"] = "GL-52 De-Escalator",
    ["323142"] = "RS-422 Railgun",
    ["323144"] = "ARC-3 Arc Thrower",
    ["323412"] = "S-11 Speargun",
    ["32342"] = "E/GL-21 Grenadier Battlement",
    ["3312"] = "Resupply",
    ["33132"] = "StA-X3 W.A.S.P. Launcher",
    ["33133"] = "FAF-14 Spear",
    ["33142"] = "LAS-99 Quasar Cannon",
    ["332311"] = "B/FLAM-80 Cremator",
    ["3333311"] = "SSSD Delivery",
    ["33412"] = "EAT-17 Expendable Anti-Tank",
    ["33413"] = "EAT-411 Leveller",
    ["33414"] = "EAT-700 Expendable Napalm",
    ["334233"] = "Prospecting Drill",
    ["334242"] = "FX-12 Shield Generator Relay",
    ["334433"] = "Activate E-711 Extraction Drill",
    ["3411"] = "MD-17 Anti-Tank Mines",
    ["3412"] = "MD-6 Anti-Personnel Minefield",
    ["34131"] = "FLAM-40 Flamethrower",
    ["34132"] = "MLS-4X Commando",
    ["34133"] = "MG-206 Heavy Machine Gun",
    ["34134"] = "TX-41 Sterilizer",
    ["341411"] = "GL-28 Belt-Fed Grenade Launcher",
    ["34142"] = "PLAS-45 Epoch",
    ["34143"] = "GL-21 Grenade Launcher",
    ["341443"] = "40-K Meltagun",
    ["34213"] = "APW-1 Anti-Materiel Rifle",
    ["34221"] = "CQC-1 One True Flag",
    ["34223"] = "CQC-9 Defoliation Tool",
    ["34224"] = "GR-8 Recoilless Rifle",
    ["342311"] = "M-1000 Maxigun",
    ["342342"] = "LIFT-182 Warp Pack",
    ["34241"] = "CQC-20 Breaching Hammer",
    ["343112"] = "AC-8 Autocannon",
    ["343113"] = "B-1 Supply Pack",
    ["343114"] = "M-105 Stalwart",
    ["34312"] = "MG-43 Machine Gun",
    ["34314"] = "LAS-98 Laser Cannon",
    ["343214"] = "MGX-42 Bullet Storm",
    ["343314"] = "SH-20 Ballistic Shield Backpack",
    ["3442"] = "MD-8 Gas Mines",
    ["3443"] = "MD-I4 Incendiary Mines",
    ["413233"] = "Hive Breaker Drill",
    ["4321241"] = "EXO-51 Lumberer Exosuit",
    ["4321431"] = "EXO-49 Emancipator Exosuit",
    ["4321433"] = "EXO-45 Patriot Exosuit",
    ["4323231"] = "M-102 Gunner FRV",
    ["432343131"] = "TD-220 Bastion MK XVI",
    ["432343142"] = "TD-110 Maelstrom",
    ["4324231"] = "EXO-55 Breakthrough Exosuit",
    ["4324311"] = "M-104 Incinerator FRV",
    ["4344312"] = "M-103 Supply FRV",
    ["44413233"] = "Aquifer Drill",
}
local options = {hide_cooldowns=true, include_grants=true, interval=0.5}
local option_specs = {
    {key='hide_cooldowns', spec={type='toggle', label='Hide Stratagems on Cooldown', default=true,
        description='Remove stratagems while their cooldown or delivery timer is active, then restore them automatically. Does not check jamming or every mission restriction.'}},
    {key='include_grants', spec={type='toggle', label='Include Mission Grants', default=true,
        description='Include mission-granted utilities, equipment and objective stratagems in the exported list.'}},
    {key='interval', spec={type='choice', label='Update Frequency', choices={'0.25 seconds','0.5 seconds','1 second'}, default=2,
        description='How often the exported list is checked. Files are rewritten only when their contents change.'}},
}
local registered_options = {}
local function service_options()
    local menu = rawget(_G, 'ModOptionsMenu')
    if type(menu) ~= 'table' or menu.api ~= 1 or type(menu.register_option) ~= 'function' or type(menu.get) ~= 'function' then return end
    for _, row in ipairs(option_specs) do
        local id = 'equippedstratagems.' .. row.key
        if registered_options[id] ~= menu then
            row.spec.mod = 'EquippedStratagems'
            local ok, result = pcall(menu.register_option, id, row.spec)
            if ok and result then registered_options[id] = menu end
        end
        if registered_options[id] == menu then
            local ok, value = pcall(menu.get, id)
            if ok then
                if row.key == 'interval' then
                    local interval = ({0.25,0.5,1})[value]
                    if interval then options.interval = interval end
                elseif type(value) == 'boolean' then options[row.key] = value end
            end
        end
    end
end
-- Eagle Rearm eligibility mirrors 0x66D650: at least one Eagle definition
-- (rearm kind +0xC8 == 49) must have fewer uses than its upgraded maximum.
-- Maximum-use calculation: 0x879550, modifier application: 0x1377330.
local function eagle_rearm_available(read, pointer, number, game, settings, payload, peer)
    local function descriptor(kind)
        assert(kind > 0 and kind < 150, 'Invalid Eagle definition')
        local at = pointer(game+TABLE_RVA+kind*8)
        assert(at >= settings and at+400 <= settings+80280, 'Eagle definition outside settings')
        assert(number(at) == kind, 'Eagle definition mismatch')
        return at
    end
    local function float(at)
        local bits = number(at)
        local exponent = math.floor(bits/8388608)%256
        local mantissa = bits%8388608
        assert(exponent < 255, 'Invalid Eagle modifier')
        local value = exponent == 0 and mantissa*2^-149 or (1+mantissa/8388608)*2^(exponent-127)
        return bits >= 2147483648 and -value or value
    end
    local manager = pointer(game+0x3326e68)
    local modifier_count = number(manager+0x38d8)
    assert(modifier_count <= 256, 'Invalid upgrade registry')
    local function maximum(kind, inherited)
        local desc = descriptor(kind)
        local value = number(desc+0x50)
        if value == 0xffffffff then return value end
        local parent = number(desc+0x10c)
        if not inherited and parent ~= 0 and number(desc+0x110)%2 == 1 then
            value = value + maximum(parent,true) - number(descriptor(parent)+0x50)
        end
        if modifier_count > 0 then
            local catalog = pointer(game+0x347cef8)
            local first, last = number(catalog+0xd1d0c), number(catalog+0xd1d10)
            assert(first <= last and last <= 4096, 'Invalid upgrade definition index')
            local taggable = false
            for i=first,last-1 do
                local index = number(catalog+0xd1d48+i*4)
                assert(index < 4096, 'Invalid upgrade definition record')
                local record = catalog+0xb9ce4+index*24
                if number(record+8) == number(desc+4) then
                    local tag_index = number(record)
                    assert(tag_index < 4096, 'Invalid upgrade tag index')
                    local tags = catalog+0x1d70+tag_index*0xb8
                    local count = number(tags)
                    assert(count <= 45, 'Invalid upgrade tag count')
                    for j=0,count-1 do
                        if number(tags+4+j*4) == 0x5001f746 then taggable=true end
                    end
                    break
                end
            end
            if taggable then
                local modifier_index
                for i=0,43 do
                    if number(game+0x32ea690+i*0x30) == 0x5001f746 then modifier_index=i; break end
                end
                if modifier_index then
                    for i=0,modifier_count-1 do
                        local registration = manager+0x38e0+i*16
                        if number(registration+8) == 0x119 then
                            local owner = pointer(registration)
                            for j=0,7 do
                                local record = owner+j*32
                                if read(record,8) == peer then
                                    local word = number(record+0x10+math.floor(modifier_index/32)*4)
                                    if math.floor(word/2^(modifier_index%32))%2 == 1 then
                                        local spec = game+0x330d2e0+modifier_index*0x30
                                        local amount = float(spec+0x28)
                                        value = number(spec+0x2c) == 0 and value*amount or value+amount
                                        value = math.floor(value)
                                    end
                                    break
                                end
                            end
                        end
                    end
                end
            end
        end
        assert(value >= 0 and value <= 1024, 'Invalid Eagle maximum uses')
        return value
    end
    local count = number(payload+0x788)
    for i=0,count-1 do
        local entry = payload+0x188+i*0x30
        local kind = number(entry)
        if kind ~= 0 and number(descriptor(kind)+0xc8) == 49 then
            local remaining = number(entry+4)
            if remaining < maximum(kind,false) then return true end
        end
    end
    return false
end

-- Consume the game's computed HUD membership rather than reimplementing its
-- objective/proximity scan. 0x183399B updates the list even while closed;
-- 0x1836747 binds each card to its payload kind/index and 0x18387E3 writes
-- membership before the visibility animation. No native functions are called.
local function hellbomb_available(read, pointer, number, game, entry_index)
    local root = pointer(game+0x346d538)
    assert(read(root+0x24e334,1) == '\1', 'Gameplay HUD not initialized')
    local state = pointer(game+0x3326340)
    assert(number(state+0xac21c) == 4, 'Gameplay HUD not active')
    local panel = root+0x24e340+0x146dc0
    local list = panel+0x1040
    for _, pair in ipairs({{panel,root+0x820},{panel+0x110,panel},
            {panel+0x220,panel+0x110},{list,panel+0x220}}) do
        assert(pointer(pair[1]+0xf0) == pair[2], 'HUD hierarchy mismatch')
    end
    for i=0,15 do
        local card = list+0x110+i*0x3760
        assert(pointer(card+0xf0) == list, 'HUD card parent mismatch')
        if number(card+0x3748) == entry_index and number(card+0x374c) == 42 then
            local active = read(card+0x36f0,1):byte()
            assert(active == 0 or active == 1, 'Invalid HUD membership')
            return active == 1
        end
    end
    return false
end
-- Selected-loadout reader. Layout evidence: installed DiverKit
-- diverkit-alpha8.10.1-preview-compact-badge-20260927 (read_equipment).
-- The player-manager block is NOT an array of equipped StratagemInfo IDs.
local BUILD_STAMP = 1790161983
local MANAGER_RVA, SESSION_RVA = 0x3326e68, 0x347cef0
local DIAGNOSTICS = 'EquippedStratagems_diagnostics.log'
local last_files, native_reader = {}, nil
local initialized, selected, was_in_mission = false, nil, false
local last_tick = nil
local last_diagnostic, pending_write = '', false
local function write_file(filename, body, force)
    if not force and last_files[filename] == body then return true end
    local loader = rawget(_G, 'CowboyBingusModLoader')
    if type(loader) ~= 'table' or type(loader.open_log) ~= 'function' then
        return false, 'Shared loader open_log is unavailable'
    end
    local opened, file = pcall(loader.open_log, filename)
    if not opened or not file then return false, 'Cannot open ' .. filename end
    -- Lua file methods report ordinary I/O failures with nil, not an exception.
    local ok, err = pcall(function()
        assert(file:write(body))
        assert(file:flush())
    end)
    local closed, result, close_error = pcall(function() return file:close() end)
    if not ok then return false, tostring(err) end
    if not closed or not result then return false, tostring(close_error or result) end
    last_files[filename] = body
    return true
end

local function reader_api()
    local injected = rawget(_G, 'EquippedStratagemsReader')
    if type(injected) == 'table' then return injected end
    if not native_reader then native_reader = windows_reader() end
    return assert(native_reader, '64-bit LuaJIT FFI is unavailable')
end

local function resolve_name(read, pointer, number, game, settings, kind, selectable)
    local descriptor = pointer(game + TABLE_RVA + kind * 8)
    assert(descriptor >= settings and descriptor+400 <= settings+80280, 'Descriptor outside stratagem settings')
    assert(number(descriptor) == kind, 'Stratagem descriptor identity mismatch')
    if selectable then assert(math.floor(number(descriptor + 0x80)/2)%2 == 1, 'Stratagem is not selectable') end
    -- Live definitions store their direction array at +0x40, with
    -- a u32 count at +0x48. Do not index the stale debug-name table.
    local code_pointer, code_count = pointer(descriptor+0x40), number(descriptor+0x48)
    assert(code_count >= 1 and code_count <= 12, 'Invalid stratagem input length')
    assert(code_pointer >= settings and code_pointer+code_count*4 <= settings+80280,
        'Stratagem input array outside settings')
    local packed, directions = read(code_pointer,code_count*4), {}
    for at=0,code_count-1 do
        local direction = u32(packed,at*4)
        assert(direction >= 1 and direction <= 4,'Invalid stratagem direction')
        directions[#directions+1] = tostring(direction)
    end
    local code = table.concat(directions)
-- Two wheel entries share this code. The supported build's definition 128
-- is explicitly "MISSIONS. Upload Discovery", not Reinforcement Pods.
    local name = (code == '42111' and kind == 128 and 'Upload Data') or CODE_NAMES[code]
    assert(name, string.format('Unsupported stratagem code %s (id %d); update the name catalog',code,kind))
    return name, code
end

local function snapshot(reader, game)
    local watched = {}
    local function read(at, size)
        local bytes = reader.read(at, size)
        assert(type(bytes) == 'string' and #bytes == size, string.format('Unreadable loadout field +%X', at-game))
        watched[#watched+1] = {at, size, bytes}
        return bytes
    end
    local function pointer(at)
        return assert(reader.pointer(read(at, 8)), 'Loadout pointer unavailable')
    end
    local function number(at) return assert(u32(read(at, 4), 0)) end
    -- Explicitly reject another build instead of interpreting arbitrary memory.
    assert(read(game, 2) == 'MZ', 'Invalid game module header')
    local pe = number(game + 0x3c)
    assert(pe >= 64 and pe <= 65536, 'Invalid PE header offset')
    assert(read(game + pe, 4) == 'PE\0\0', 'Invalid PE signature')
    assert(number(game + pe + 8) == BUILD_STAMP, 'Unsupported game build; reader needs an updated layout')
    local function finish()
        for _, field in ipairs(watched) do
            assert(reader.read(field[1], field[2]) == field[3], "Loadout changed during read; retrying")
        end
    end
    return read, pointer, number, finish
end

local function selection(reader, game)
    local read, pointer, number, finish = snapshot(reader, game)
    local manager = pointer(game + MANAGER_RVA)
    local bucket = read(manager + 0x62a0, 24)
    local count = u32(bucket, 0)
    if count == 0 then return nil, 'Selection screen is not registered' end
    assert(count == 1 and u32(bucket, 16) == 0xe5, 'Unexpected loadout registry layout')
    local owner = assert(reader.pointer(bucket, 8), 'Loadout owner unavailable')
    local slot = number(owner + 0x27d0)
    assert(slot < 4, 'Local player slot unavailable')
    local session = pointer(game + SESSION_RVA)
    local peer = read(session + 0xb398, 8)
    assert(peer ~= string.rep('\0', 8), 'Local player identity unavailable')
    local record = owner + slot * 0x9f0
    assert(read(record + 0x9f8, 8) == peer, 'Loadout does not belong to the local player')
    local card
    for i = 0, 3 do
        local candidate = owner + 0x53a78 + i * 0x1ee18
        local header = read(candidate + 0x1edf0, 16)
        if reader.pointer(header) == record + 0x10 and u32(header, 12) == slot then
            assert(not card, 'Ambiguous local player card')
            card = candidate
        end
    end
    assert(card, 'Local player card unavailable')
    local available, available_count = {}, number(record + 0x798)
    assert(available_count <= 32, 'Invalid payload stratagem count')
    for i = 0, available_count - 1 do
        local kind = number(record + 0x198 + i * 0x30)
        assert(kind < 150, 'Invalid payload stratagem ID')
        available[kind] = (available[kind] or 0) + 1
    end
    local settings = pointer(game + 0x348e8f8)
    local names, details = {}, {}
    for i = 0, 3 do
        local kind = number(card + 0x5b78 + 0x8ec0 + 0x128c + i * 0x12a8)
        assert(kind < 150, 'Invalid selected stratagem ID')
        if kind ~= 0 then
            assert(available[kind] and available[kind] > 0, 'Selected slot does not match the local payload')
            available[kind] = available[kind] - 1
            local name, code = resolve_name(read, pointer, number, game, settings, kind, true)
            names[#names+1] = name
            details[#details+1] = string.format('slot=%d id=%d code=%s name=%s', i+1, kind, code, name)
        end
    end
    finish()
    return {names=names, details=details, source='local selection screen'}, 'Selection captured'
end

-- SEAF's payload entry exists before the objective enables the artillery.
-- Mirror the supported build's gate at 0x66CA6C and ammunition enumeration
-- at 0xB56ECE: controller type 0x65, live ammunition count and enabled order.
local function upload_available(read, pointer, number, game)
    -- Native 0x6F24D0 writes the local-player in-range flag at config +0x26.
    -- Check its prerequisite objective flags too: an old proximity bit alone
    -- must not reactivate a completed or disabled objective (0x6F3100).
    local controller = pointer(game+0x3326530)
    local count = number(controller+0xc)
    assert(count <= 256, 'Invalid upload objective count')
    if count == 0 then return false end
    local configs, states = pointer(controller+0x38), pointer(controller+0x40)
    for i=0,count-1 do
        local config, state = configs+i*0x2c, states+i*0x40
        local flags = read(config+0x24,6)
        local status = read(state+0x28,1):byte()
        local tail = read(state+0x38,2)
        local active = status ~= 0 or flags:byte(5) ~= 0
            or (flags:byte(6) ~= 0 and number(state) > 0)
        if active and tail:byte(2) == 0 and flags:byte(1) == 0 and flags:byte(2) == 0
            and not (flags:byte(6) ~= 0 and tail:byte(1) ~= 0)
            and flags:byte(3) ~= 0 then return true end
    end
    return false
end

local function seaf_available(read, pointer, number, game)
    local manager = pointer(game + MANAGER_RVA)
    local count = number(manager+0x1cb8)
    assert(count <= 256, 'Invalid mission availability registry count')
    local invalid_unit = number(game+0x3483c4c)
    local found, ready = false, true
    for i=0,count-1 do
        local registration = manager+0x1cc0+i*0x10
        if number(registration+8) == 0x65 then
            found = true
            local controller = pointer(registration)
            local shells = number(controller+0xc)
            assert(shells <= 256, 'Invalid SEAF ammunition record count')
            local best_order, unit = 0xffffffff, invalid_unit
            if shells > 0 then
                local ammo = pointer(controller+0x50)
                local units = pointer(controller+0x38)
                for j=0,shells-1 do
                    local shell = ammo+j*0x2c
                    local order = number(shell+0x24)
                    if order ~= 0xffffffff and number(shell) ~= 0 and order < best_order then
                        best_order = order
                        unit = number(pointer(units+j*8)+8)
                    end
                end
            end
            if unit == invalid_unit then ready = false end
        end
    end
    return found and ready
end

-- Supported-build native HUD (0x1834A10/0x1836510) reads this same
-- peer-owned payload. Entries include grants; cooldown/charge timers are not
-- membership fields and must not make an otherwise stable snapshot fail.
local function mission_loadout(reader, game)
    local read, pointer, number, finish = snapshot(reader, game)
    local session = pointer(game + SESSION_RVA)
    local peer = read(session + 0xb398, 8)
    assert(peer ~= string.rep('\0',8), 'Local player identity unavailable')
    local root = pointer(game + 0x347ce50)
    local count = number(root + 0x2d200)
    assert(count <= 32, 'Invalid mission player count')
    local payload
    for i=0,count-1 do
        local record = root + i*0x1690
        if read(record,8) == peer then
            assert(not payload, 'Ambiguous local mission payload')
            payload = record + 0x38
        end
    end
    assert(payload, 'Local mission payload unavailable')
    local entries = number(payload + 0x788)
    assert(entries <= 32, 'Invalid mission stratagem count')
    local settings = pointer(game + 0x348e8f8)
    -- Native HUD compares entry +0x18 (cooldown) and +0x20 (delivery)
    -- against the simulation clock at *(game+0x3326348)+0x18.
    -- Reinforce uses the shared mission timer rather than entry +0x18.
    local now
    if options.hide_cooldowns then
        local clock = pointer(game + 0x3326348)
        now = reader.read(clock+0x18,8) -- Clock advances during a snapshot.
        assert(type(now)=='string' and #now==8, 'Simulation clock unavailable')
    end
    local function future(timestamp)
        local hi, lo = u32(timestamp,4), u32(timestamp,0)
        local now_hi, now_lo = u32(now,4), u32(now,0)
        return hi > now_hi or (hi == now_hi and lo > now_lo)
    end
    local names, details, seen = {}, {}, {}
    for i=0,entries-1 do
        local entry = payload + 0x188 + i*0x30
        local kind = number(entry)
        assert(kind < 150, 'Invalid mission stratagem ID')
        if kind ~= 0 then
            local granted = read(entry+9,1):byte() ~= 0
            local name, code = resolve_name(read, pointer, number, game, settings, kind, false)
            local cooling = false
            if options.hide_cooldowns then
                local cooldown = read(entry+0x18,8)
                if kind == 124 then
                    local mission_state = pointer(game + MISSION_RVA)
                    cooldown = number(mission_state+8) ~= 0 and read(mission_state+0x50,8) or string.rep('\0',8)
                end
                cooling = future(cooldown) or future(read(entry+0x20,8))
            end
            local available, gate = true, 'payload'
            if kind == 42 then
                local checked, result = pcall(hellbomb_available, read, pointer, number, game, i)
                available = checked and result == true
                gate = checked and (available and 'hellbomb_hud_available' or 'hellbomb_context_inactive') or 'hellbomb_state_unreadable'
            elseif kind == 28 then
                local checked, result = pcall(seaf_available, read, pointer, number, game)
                available = checked and result == true
                gate = checked and (available and 'seaf_enabled' or 'seaf_locked_or_empty') or 'seaf_state_unreadable'
            elseif kind == 128 then
                local checked, result = pcall(upload_available, read, pointer, number, game)
                available = checked and result == true
                gate = checked and (available and 'upload_in_range' or 'upload_inactive_or_out_of_range') or 'upload_state_unreadable'
            elseif kind == 49 then
                local checked, result = pcall(eagle_rearm_available, read, pointer, number, game, settings, payload, peer)
                available = checked and result == true
                gate = checked and (available and 'eagle_uses_spent' or 'eagle_fully_stocked') or 'eagle_state_unreadable'
            end
            local included = available and (options.include_grants or not granted) and not cooling
            if included and not seen[name] then names[#names+1]=name; seen[name]=true end
            details[#details+1] = string.format('entry=%d id=%d granted=%s cooldown=%s gate=%s exported=%s code=%s name=%s',i+1,kind,tostring(granted),tostring(cooling),gate,tostring(included),code,name)
        end
    end
    finish()
    return {names=names, details=details, source='local mission payload'}, 'Mission list captured'
end

local function in_mission(reader, game)
    local pointer = reader.pointer(reader.read(game + MISSION_RVA, 8))
    if not pointer then return nil end
    local bytes = reader.read(pointer, 0x44)
    if type(bytes) ~= 'string' or #bytes ~= 0x44 then return nil end
    if u32(bytes, 8) == 0 then return false end
    local mode = u32(bytes, 0x40)
    return mode >= 1 and mode <= 7
end

local function flush_loadout(force)
    service_options()
    if not initialized then
        local ok, why = write_file(LOG_NAME, '', true)
        if not ok then api.status = why; return false end
        initialized = true
    end
    local mission, state, reason
    local ok, failure = pcall(function()
        local reader = reader_api()
        local game = assert(reader.module('game.dll'), 'game.dll unavailable')
        assert(usable_address(game), 'Invalid game module address')
        mission = in_mission(reader, game)
        if mission == true then
            state, reason = mission_loadout(reader, game)
        else
            state, reason = selection(reader, game)
        end
    end)
    if not ok then
        reason = tostring(failure)
        if reason:find('Unsupported stratagem code',1,true) then selected = nil end
    end
    if state then
        selected = state
    elseif mission == false and was_in_mission then
        selected = nil
    end
    if mission ~= nil then was_in_mission = mission end
    local names = selected and selected.names or {}
    local body = #names > 0 and table.concat(names, '\n') .. '\n' or ''
    local wrote, write_error = write_file(LOG_NAME, body, force or pending_write)
    -- Framed companion snapshot lets consumers distinguish an authoritative
    -- empty list from an incomplete concurrent read or a legacy missing log.
    local frame = 'EquippedStratagems snapshot 1\ncount=' .. #names .. '\n' .. body .. 'END\n'
    local snapshot_ok, snapshot_error = write_file('EquippedStratagems_state.log', frame, force or pending_write)
    if not snapshot_ok then wrote=false; write_error=snapshot_error end
    pending_write = not wrote
    if wrote then api.names = names end
    api.status = wrote and (state and 'captured' or (selected and 'retained last valid list' or 'waiting for local loadout')) or write_error
    last_diagnostic = 'EquippedStratagems revision 9\nstatus=' .. tostring(api.status)
        .. '\nhide_cooldowns=' .. tostring(options.hide_cooldowns) .. '\ninclude_grants=' .. tostring(options.include_grants)
        .. '\nreader=' .. tostring(reason) .. '\ncount=' .. #names
        .. '\nmission=' .. tostring(mission)
        .. '\nsource=' .. (state and state.source or (selected and ('cached '..selected.source) or 'none'))
        .. '\n'
    if selected then
        last_diagnostic = last_diagnostic .. table.concat(selected.details, '\n') .. '\n'
    end
    write_file(DIAGNOSTICS, last_diagnostic, force)
    return wrote and selected ~= nil
end

function api.refresh() return flush_loadout(true) end

function api.publish(raw)
    local list = as_name_list(raw)
    if not list or #list > MAX_EQUIPPED then return false end
    local names = {}
    for _, name in ipairs(list) do
        local resolved = CATALOG[fold(name)]
        if not resolved then return false end
        names[#names+1] = resolved
    end
    local body = #names > 0 and table.concat(names, '\n') .. '\n' or ''
    local ok = write_file(LOG_NAME, body, true)
    local framed = write_file('EquippedStratagems_state.log',
        'EquippedStratagems snapshot 1\ncount=' .. #names .. '\n' .. body .. 'END\n', true)
    ok = ok and framed
    if ok then api.names = names end
    return ok
end

local function service_binding()
    local menu = rawget(_G, 'ModBindingsMenu')
    if type(menu) ~= 'table' or menu.api ~= 1 or type(menu.register_binding) ~= 'function' then return end
    if not binding_registered then
        local called, ok = pcall(menu.register_binding, BINDING_ID, BINDING_LABEL, nil, {category='EquippedStratagems'})
        if not called or not ok then return end
        binding_registered = true
    end
    if type(menu.is_down) ~= 'function' then return end
    local ok, down = pcall(menu.is_down, BINDING_ID)
    if ok then
        if down and not binding_down then flush_loadout(true) end
        binding_down = down
    end
end

rawset(_G, 'EquippedStratagems', api)
local previous_update = rawget(_G, 'update')
local function after_update(dt, ...)
    local ok, why = pcall(function()
        service_binding()
        -- Some update chains supply no dt. Use Windows monotonic time when
        -- available so that a successful first export is not the last poll.
        local clock_ok, now = pcall(function()
            local reader = reader_api()
            return type(reader.clock) == 'function' and reader.clock() or nil
        end)
        local step = type(dt) == 'number' and dt >= 0 and dt or 0
        if clock_ok and type(now) == 'number' then
            if last_tick then step = math.max(0, now-last_tick) end
            last_tick = now
        end
        elapsed = elapsed + step
        if elapsed >= options.interval then elapsed = 0; flush_loadout(false) end
    end)
    if not ok then
        api.status = tostring(why)
        write_file(DIAGNOSTICS, 'runtime_error=' .. tostring(why) .. '\n')
    end
    return ...
end
update = function(dt, ...)
    if type(previous_update) == 'function' then
        return after_update(dt, previous_update(dt, ...))
    end
    return after_update(dt)
end
print('[EquippedStratagems] revision 9 loaded')
