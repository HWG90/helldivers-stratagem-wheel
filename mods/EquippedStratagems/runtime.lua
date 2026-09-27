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
            if kind == 28 then
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
    last_diagnostic = 'EquippedStratagems revision 8\nstatus=' .. tostring(api.status)
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
print('[EquippedStratagems] revision 8 loaded')
