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
