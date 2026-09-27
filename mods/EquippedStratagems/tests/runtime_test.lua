local ffi = require('ffi')
local function bytes(value, size)
    local b = ffi.new('uint64_t[1]', value)
    return ffi.string(b, size or 8)
end
local game, manager, owner, session, card = 0x10000000, 0x20000000, 0x21000000, 0x22000000, 0x21053a78
local memory, files, writes, closed, failure, unstable
local function put(at, value) memory[#memory+1] = {at, value} end
local function read(at, size)
    for i = #memory, 1, -1 do
        local block = memory[i]
        if at >= block[1] and at + size <= block[1] + #block[2] then
            return block[2]:sub(at-block[1]+1, at-block[1]+size)
        end
    end
end
local function pointer(blob, offset)
    offset = offset or 0
    if not blob or #blob < offset+8 then return nil end
    local b = ffi.new('uint64_t[1]')
    ffi.copy(b, blob:sub(offset+1, offset+8), 8)
    local value = tonumber(b[0])
    if value >= 0x10000 then return value end
end
local function slots(kinds, keys)
    put(owner+0x798, bytes(#kinds, 4))
    for i=0,3 do
        local kind = kinds[i+1] or 0
        put(card+0x5b78+0x8ec0+0x128c+i*0x12a8, bytes(kind,4))
        if kind ~= 0 then
            put(owner+0x198+i*0x30,bytes(kind,4))
            local desc, code_at = 0x24000000+kind*400, 0x24000000+60000+kind*64
            put(game+0x37cb600+kind*8,bytes(desc))
            put(desc,bytes(kind,4)); put(desc+0x80,bytes(2,4))
            local codes={Autocannon='343112',OrbitalGatlingBarrage='23411',EagleBomb='12333',Orbital120='223423'}
            local code=codes[keys[i+1]] or '111111111111'
            local packed={}
            for d in code:gmatch('.') do packed[#packed+1]=bytes(tonumber(d),4) end
            put(desc+0x40,bytes(code_at));put(desc+0x48,bytes(#code,4));put(code_at,table.concat(packed))
        end
    end
end
local function setup()
    memory, files, writes, closed, failure, unstable = {}, {}, {}, 0, nil, false
    EquippedStratagems=nil; update=nil
    EquippedStratagemsReader={module=function() return game end, pointer=pointer, read=function(at,n)
        local result=read(at,n)
        if unstable and at==card+0x5b78+0x8ec0+0x128c then
            unstable=false; put(at,bytes(0,4))
        end
        return result
    end}
    CowboyBingusModLoader={open_log=function(name)
        assert(name:match('^[%w_-]+%.log$'), 'Filename rejected by shared loader')
        local body=''
        writes[name]=(writes[name] or 0)+1
        if failure=='open' and name=='EquippedStratagems.log' then return nil end
        files[name]=''
        return {
            write=function(self, value)
                if failure=='write' and name=='EquippedStratagems.log' then return nil,'disk full' end
                body=body..value;files[name]=body;return self
            end,
            flush=function()
                if failure=='flush' and name=='EquippedStratagems.log' then return nil,'flush failed' end
                return true
            end,
            close=function()
                closed=closed+1
                if failure=='close' and name=='EquippedStratagems.log' then return nil,'close failed' end
                return true
            end,
        }
    end}
    ModBindingsMenu=nil;ModOptionsMenu=nil
    put(game,'MZ');put(game+60,bytes(128,4));put(game+128,'PE\0\0');put(game+136,bytes(1790161983,4))
    put(game+0x3326e68,bytes(manager));put(game+0x347cef0,bytes(session))
    put(game+0x348e8f8,bytes(0x24000000))
    put(manager+0x62a0,bytes(1,8)..bytes(owner)..bytes(0xe5,8))
    put(owner+0x27d0,bytes(0,4));put(session+0xb398,'LOCAL123');put(owner+0x9f8,'LOCAL123')
    for i=0,3 do put(owner+0x53a78+i*0x1ee18+0x1edf0,string.rep('\0',16)) end
    put(card+0x1edf0,bytes(owner+0x10)..bytes(0,8))
    put(game+0x33266a0,bytes(0x25000000));put(0x25000000,string.rep('\0',0x44))
    put(0x25000000+0x50,bytes(0))
    put(game+0x3326348,bytes(0x27000000));put(0x27000000+0x18,bytes(1000))
    slots({1,2},{'Autocannon','OrbitalGatlingBarrage'})
    dofile('EquippedStratagems.lua')
end
local expected='AC-8 Autocannon\nOrbital Gatling Barrage\n'
setup();update(0.5)
assert(files['EquippedStratagems.log']==expected,'automatic poll without opening Ctrl menu')
assert(not files['EquippedStratagems.log']:find('#'),'names only')
local count=writes['EquippedStratagems.log'];update(0.5)
assert(writes['EquippedStratagems.log']==count,'unchanged selection should not churn disk')
assert(EquippedStratagems.refresh());assert(writes['EquippedStratagems.log']==count+1,'manual refresh rewrites')
slots({2},{'OrbitalGatlingBarrage'});update(0.5)
assert(files['EquippedStratagems.log']=='Orbital Gatling Barrage\n','single selected slot')
slots({},{});update(0.5);assert(files['EquippedStratagems.log']=='','empty selection clears')

setup();put(owner+0x9f8,'OTHER123');update(0.5)
assert(files['EquippedStratagems.log']=='','reject other player')
assert(files['EquippedStratagems_diagnostics.log']:find('local player',1,true))
setup();unstable=true;update(0.5);assert(files['EquippedStratagems.log']=='','reject a torn snapshot')
setup();put(game+136,bytes(1,4));update(0.5)
assert(files['EquippedStratagems.log']=='','reject unsupported game')
assert(files['EquippedStratagems_diagnostics.log']:find('Unsupported game build',1,true))

setup();update(0.5)
put(manager+0x62a0,bytes(0,8)..bytes(owner)..bytes(0xe5,8))
put(0x25000000,string.rep('\0',8)..bytes(1,4)..string.rep('\0',0x40-12)..bytes(1,4))
update(0.5);assert(files['EquippedStratagems.log']==expected,'retain selection during mission')
put(0x25000000,string.rep('\0',0x44));update(0.5)
assert(files['EquippedStratagems.log']=='','clear completed mission selection')

for _, mode in ipairs({'open','write','flush','close'}) do
    setup();failure=mode;update(0.5)
    failure=nil;update(0.5)
    assert(files['EquippedStratagems.log']==expected,'retry failed '..mode)
end
setup();update(0.5);failure='write';slots({2},{'OrbitalGatlingBarrage'});update(0.5)
local closed_before=closed;failure=nil;update(0.5)
assert(closed>closed_before and files['EquippedStratagems.log']=='Orbital Gatling Barrage\n','retry after failed update')

setup();slots({1},{'UnknownNewStratagem'});update(0.5)
assert(files['EquippedStratagems.log']=='','unmapped code must not export a wrong name')
assert(files['EquippedStratagems_diagnostics.log']:find('Unsupported stratagem code',1,true))
assert(not EquippedStratagems.publish({'Autocannon','Not in catalog'}),'reject partial publish')

setup();local down=false
ModBindingsMenu={api=1,register_binding=function() return true end,is_down=function() return down end}
update(0.5);local before=writes['EquippedStratagems.log'];down=true;update(0.01)
assert(writes['EquippedStratagems.log']==before+1,'binding forces export')
update(0.01);assert(writes['EquippedStratagems.log']==before+1,'held binding does not spam')
setup();local loader=CowboyBingusModLoader;CowboyBingusModLoader=nil;update(0.5)
CowboyBingusModLoader=loader;update(0.5);assert(files['EquippedStratagems.log']==expected,'late loader retries')
setup();local now=10;EquippedStratagemsReader.clock=function() return now end
update();assert(files['EquippedStratagems.log']==expected)
slots({2},{'OrbitalGatlingBarrage'});now=11;update()
assert(files['EquippedStratagems.log']=='Orbital Gatling Barrage\n','poll without dt via monotonic clock')
-- IDs and direction codes confirmed by the user's live revision 3 capture.
setup();slots({3,136,4,25},{'EagleBomb','Orbital120','OrbitalGatlingBarrage','Autocannon'});update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\nOrbital 120mm HE Barrage\nOrbital Gatling Barrage\nAC-8 Autocannon\n','user loadout mapping')

setup();EquippedStratagems=nil
update=function(dt,tag) assert(dt==0.5 and tag=='input');return 'return',nil,42 end
dofile('EquippedStratagems.lua')
local a,b,c=update(0.5,'input');assert(a=='return' and b==nil and c==42,'preserve chained update tuple')
-- Live mission payload has grants and may be read without a selection capture.
local mission_root=0x26000000
local function mission_entries(kinds, peer)
    put(game+0x3326530,bytes(0x29000000));put(0x2900000c,bytes(1,4))
    put(0x29000038,bytes(0x29100000));put(0x29000040,bytes(0x29200000))
    put(0x29100024,string.char(0,0,1,0,0,0))
    put(0x29200028,string.char(1));put(0x29200038,string.char(0,0))
    put(0x25000000,string.rep('\0',8)..bytes(1,4)..string.rep('\0',0x40-12)..bytes(1,4))
    put(game+0x347ce50,bytes(mission_root))
    put(mission_root+0x2d200,bytes(2,4))
    put(mission_root,'REMOTE12')
    local record=mission_root+0x1690
    put(record,peer or 'LOCAL123')
    local payload=record+0x38
    put(payload+0x788,bytes(#kinds,4))
    local codes={[3]='12333',[136]='223423',[4]='23411',[25]='343112',
        [124]='13241',[145]='1321',[33]='3312',[50]='432343142',[128]='42111',[28]='2113',[49]='11412'}
    for i,kind in ipairs(kinds) do
        put(payload+0x188+(i-1)*0x30,bytes(kind,4))
        put(payload+0x191+(i-1)*0x30,string.char(i>4 and 1 or 0))
        put(payload+0x188+(i-1)*0x30+0x18,bytes(0)..bytes(0))
        if kind~=0 then
            local desc,code_at=0x24000000+kind*400,0x24000000+60000+kind*64
            put(game+0x37cb600+kind*8,bytes(desc));put(desc,bytes(kind,4))
            put(desc+0x80,bytes(0,4)) -- Grants need not be selectable.
            local code=codes[kind] or '111111111111';local packed={}
            for d in code:gmatch('.') do packed[#packed+1]=bytes(tonumber(d),4) end
            put(desc+0x40,bytes(code_at));put(desc+0x48,bytes(#code,4));put(code_at,table.concat(packed))
        end
    end
    return payload
end
local all='Eagle 500kg Bomb\nOrbital 120mm HE Barrage\nOrbital Gatling Barrage\nAC-8 Autocannon\nReinforce\nSoS Beacon\nResupply\nTD-110 Maelstrom\n'
setup();mission_entries({3,136,4,25,124,145,33,50});update(0.5)
assert(files['EquippedStratagems.log']==all,'selected plus grants, local second record, no selection capture')
assert(files['EquippedStratagems_diagnostics.log']:find('source=local mission payload',1,true))
mission_entries({3,136,4,25,124,145,33,50,128});update(0.5)
assert(files['EquippedStratagems.log']==all..'Upload Data\n','objective appears')
mission_entries({3,136,4,25,124,145,33,50});update(0.5)
assert(files['EquippedStratagems.log']==all,'objective disappears')
mission_entries({124,124,0});update(0.5)
assert(files['EquippedStratagems.log']=='Reinforce\n','duplicate names and vacant entries omitted')
local payload=mission_entries({33});local oldread=EquippedStratagemsReader.read;local torn=true
EquippedStratagemsReader.read=function(at,n)
    local result=oldread(at,n)
    if torn and at==payload+0x188 then torn=false;put(at,bytes(124,4)) end
    return result
end
update(0.5);assert(files['EquippedStratagems.log']=='Reinforce\n','mission membership changed during capture')
assert(files['EquippedStratagems_diagnostics.log']:find('changed during read',1,true))
mission_entries({});update(0.5);assert(files['EquippedStratagems.log']=='','empty live list clears')
setup();mission_entries({124},'REMOTE34');update(0.5)
assert(files['EquippedStratagems.log']=='','remote mission payload rejected')
setup();mission_entries({124});put(game+136,bytes(1,4));update(0.5)
assert(files['EquippedStratagems.log']=='','mission reader rejects unsupported build')
setup();mission_entries({124,149});update(0.5)
assert(files['EquippedStratagems.log']=='','unknown mission kind cannot produce a partial list')
print('PASS: selection and mission identity, grants, objective changes, stability, lifecycle, names, I/O retries, refresh and update chaining')

setup();local payload=mission_entries({3,136,4,25,124,145,33,50});update(0.5)
put(payload+0x188+0x18,bytes(2000));update(0.5)
assert(not files['EquippedStratagems.log']:find('Eagle 500kg',1,true),'hide active cooldown')
put(0x27000000+0x18,bytes(2000));update(0.5)
assert(files['EquippedStratagems.log']==all,'restore at exact cooldown expiry')
put(payload+0x188+0x20,bytes(2500));update(0.5)
assert(not files['EquippedStratagems.log']:find('Eagle 500kg',1,true),'hide during delivery')
put(0x25000000+0x50,bytes(3000));update(0.5)
assert(not files['EquippedStratagems.log']:find('Reinforce',1,true),'shared Reinforce cooldown')
local saved={hide_cooldowns=false,include_grants=false,interval=1};local registrations=0
ModOptionsMenu={api=1,register_option=function(id,spec) registrations=registrations+1;return true end,
    get=function(id) return saved[id:match('%.(.+)$')] end}
update(0.5)
assert(registrations==3,'late options registration')
assert(files['EquippedStratagems.log']==all:match('^(.-)Reinforce'),'applied grants filter and cooldown disabled')
saved.include_grants=true;update(0.25)
assert(files['EquippedStratagems.log']==all,'updated applied option')
assert(registrations==3,'register once')
saved.hide_cooldowns=true;mission_entries({3});put(payload+0x188+0x18,bytes(9000));update(0.25)
assert(files['EquippedStratagems.log']=='','all entries cooling clears names')
assert(files['EquippedStratagems_state.log']=='EquippedStratagems snapshot 1\ncount=0\nEND\n','complete empty snapshot')
print('PASS: cooldown and delivery expiry, shared Reinforce timer, options, authoritative empty snapshot')

setup();mission_entries({3,28})
local controller,ammo,units,unit=0x28000000,0x28100000,0x28200000,0x28300000
put(game+0x3483c4c,bytes(0xffffffff,4))
put(manager+0x1cb8,bytes(1,4));put(manager+0x1cc0,bytes(controller));put(manager+0x1cc8,bytes(0x65,4))
put(controller+0xc,bytes(1,4));put(controller+0x50,bytes(ammo));put(controller+0x38,bytes(units))
put(units,bytes(unit));put(unit+8,bytes(123,4))
put(ammo,bytes(5,4));put(ammo+0x24,bytes(0xffffffff,4))
update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\n','SEAF preloaded ammunition is not an enabled grant')
put(ammo+0x24,bytes(0,4));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\nSEAF Artillery\n','SEAF appears after game enables ammunition order')
put(ammo,bytes(0,4));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\n','SEAF disappears when ammunition exhausted')
put(ammo,bytes(5,4));put(unit+8,bytes(0xffffffff,4));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\n','invalid artillery unit cannot enable SEAF')
put(manager+0x1cb8,bytes(0,4));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\n','missing controller cannot enable SEAF')
setup();mission_entries({3,28});update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\n','unreadable SEAF state omits only SEAF')
print('PASS: SEAF locked, enabled, depleted, invalid unit, missing and unreadable controller')

setup();mission_entries({3,128});put(0x29100024,string.char(0,0,0,0,0,0));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\n','upload omitted outside objective radius')
put(0x29100024,string.char(0,0,1,0,0,0));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\nUpload Data\n','upload appears in active objective radius')
put(0x29200038,string.char(0,1));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\n','completed objective cannot use stale proximity bit')
put(0x29200038,string.char(0,0));put(0x29200028,string.char(0));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\n','inactive objective hidden')
put(0x2900000c,bytes(0,4));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\n','no upload objectives hidden')
print('PASS: upload proximity, active objective, completion and absent objective gates')

setup();local payload=mission_entries({3,49})
put(manager+0x38d8,bytes(0,4))
local eagle_desc=0x24000000+3*400
put(eagle_desc+0xc8,bytes(49,4));put(eagle_desc+0x50,bytes(2,4));put(eagle_desc+0x10c,bytes(0,4))
put(0x24000000+49*400+0xc8,bytes(0,4))
put(payload+0x188+4,bytes(2,4));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\n','full Eagle stock hides Rearm')
put(payload+0x188+4,bytes(1,4));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\nEagle Rearm\n','spent Eagle use enables Rearm')
put(payload+0x188+4,bytes(2,4));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\n','replenished stock hides Rearm again')
-- Upgrade adds one use for this local peer; remaining two is now below max 3.
put(manager+0x38d8,bytes(1,4));put(manager+0x38e0,bytes(0x2b000000));put(manager+0x38e8,bytes(0x119,4))
put(0x2b000000,'LOCAL123');put(0x2b000010,bytes(1,4))
put(game+0x347cef8,bytes(0x2c000000));put(0x2c0d1d0c,bytes(0,4));put(0x2c0d1d10,bytes(1,4))
put(0x2c0d1d48,bytes(0,4));put(0x2c0b9ce4,bytes(0,4));put(0x2c0b9cec,bytes(12345,4))
put(eagle_desc+4,bytes(12345,4));put(0x2c001d70,bytes(1,4));put(0x2c001d74,bytes(0x5001f746,4))
put(game+0x32ea690,bytes(0x5001f746,4));put(game+0x330d2e0+0x28,bytes(0x3f800000,4));put(game+0x330d2e0+0x2c,bytes(1,4))
update(0.5);assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\nEagle Rearm\n','upgraded max is respected')
put(payload+0x188+4,bytes(3,4));update(0.5)
assert(files['EquippedStratagems.log']=='Eagle 500kg Bomb\n','full upgraded stock hides Rearm')
print('PASS: Eagle Rearm full/spent/replenished stock and local upgrade eligibility')
