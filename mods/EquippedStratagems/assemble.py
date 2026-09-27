"""Rebuild the single addon entry from its catalog, helpers and runtime."""
from pathlib import Path

root = Path(__file__).resolve().parent
header = '''-- HD2-Addon: mods/EquippedStratagems/EquippedStratagems
-- Exports the local player's selected and mission-granted stratagems, one name per line.
local prior = rawget(_G, 'EquippedStratagems')
if type(prior) == 'table' and prior.mod == 'EquippedStratagems' then return end
local LOG_NAME = 'EquippedStratagems.log'
local TABLE_RVA, MISSION_RVA = 0x37cb600, 0x33266a0
local BINDING_ID, BINDING_LABEL = 'equippedstratagems.send_strategems', 'Send Strategems'
local POLL_SECONDS, MAX_EQUIPPED = 0.5, 32
local api = {api=1, mod='EquippedStratagems', revision=9, names=nil}
local elapsed, binding_registered, binding_down = POLL_SECONDS, false, false
'''
(root / 'EquippedStratagems.lua').write_text(header + (root / 'common.lua').read_text() + (root / 'codes.lua').read_text() + (root / 'options.lua').read_text() + (root / 'eligibility.lua').read_text() + (root / 'runtime.lua').read_text(), encoding='utf-8', newline='\n')
