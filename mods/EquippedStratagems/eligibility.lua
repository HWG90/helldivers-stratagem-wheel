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
