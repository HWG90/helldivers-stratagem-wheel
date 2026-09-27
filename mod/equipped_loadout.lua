-- HD2-Addon: mods/stratagemwheel/equipped_loadout

-- Writes the equipped stratagem list for the stratagem wheel.
-- Uses the shared loader's open_log and the update callback those addons
-- already chain. It does not read process memory, patch code, or hide itself.

if rawget(_G, 'StratagemWheelLoadout') then return end

local LOG_NAME = 'EquippedStratagems.log'
local POLL_SECONDS = 0.5
local FUNCTION_NAMES = {'equipped', 'loadout', 'slots', 'names', 'get_loadout', 'equipped_stratagems', 'current'}
local SETTING_KEYS = {'equipped_stratagems', 'stratagem_loadout', 'stratagems', 'loadout'}

local api = {names = nil}
local last_body = nil
local elapsed = POLL_SECONDS

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
        if key ~= 'mods/stratagemwheel/equipped_loadout'
            and (folded:find('stratagem', 1, true) or folded:find('loadout', 1, true)) then
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
    for _, key in ipairs({'EquippedStratagems', 'StratagemLoadout', 'PlayerLoadout'}) do
        local names = as_name_list(rawget(_G, key))
        if names then return names end
    end
    return nil
end

local function collect()
    if api.names then return api.names end
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

function api.publish(names)
    local list = as_name_list(names)
    if not list then return false end
    api.names = list
    write_names(list)
    return true
end

rawset(_G, 'StratagemWheelLoadout', api)

local previous_update = rawget(_G, 'update')
update = function(dt, ...)
    elapsed = elapsed + (type(dt) == 'number' and dt or 0)
    if elapsed >= POLL_SECONDS then
        elapsed = 0
        local names = collect()
        if names then write_names(names) end
    end
    if type(previous_update) == 'function' then return previous_update(dt, ...) end
end
