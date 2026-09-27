-- Real Windows API calls in the isolated Lua test process, never the game.
local ffi = require('ffi')
ffi.cdef[[
void *GetModuleHandleA(const char *name);
void *GetCurrentProcess(void);
uint64_t GetTickCount64(void);
int ReadProcessMemory(void *, const void *, void *, size_t, size_t *);
short GetAsyncKeyState(int);
]]
local logs={}
CowboyBingusModLoader={open_log=function(name)
    assert(name:match('^[%w_-]+%.log$'))
    logs[name]=''
    return {write=function(self,text) logs[name]=logs[name]..text;return self end,
        flush=function() return true end,close=function() return true end}
end}
dofile('EquippedStratagems.lua')
update()
assert(logs['EquippedStratagems.log']=='')
assert(logs['EquippedStratagems_diagnostics.log']:find('game.dll unavailable',1,true))
print('PASS: real Windows FFI initialization alongside existing declarations')
