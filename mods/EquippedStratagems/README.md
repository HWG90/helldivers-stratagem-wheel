# EquippedStratagems

Exports the local player's selected and mission-granted stratagems to a plain text file:

`%LOCALAPPDATA%\CowboyBingus\Helldivers2\Logs\EquippedStratagems.log`

Install `EquippedStratagems.zip` through your mod manager, replacing the old
version. Keep Bingus Shared Loader enabled. The list updates automatically on
the selection screen and in mission. Mod Bindings Menu is optional; its **Send Strategems** binding forces a
refresh. See [INSTALL.txt](INSTALL.txt).

Revision 8 reads the live local player's payload in mission, including granted
utilities, equipment and objective stratagems. It does not require a previous
selection-screen capture. By default, names with active cooldown or delivery
timers are omitted and restored automatically at expiry. This is timer filtering,
not a complete readiness check: depleted charges, jamming and other contextual
restrictions are not modeled. Duplicate names and empty entries are omitted.
New game sessions clear the previous output. Transient read failures retain the
last valid list, with the failure reason in diagnostics.

The mission layout was traced from the supported game's native HUD reader:
root at `game.dll+0x347ce50`, up to 32 peer-owned records with stride `0x1690`,
payload at record `+0x38`, entry count at payload `+0x788`, entries at `+0x188`
with stride `0x30`. It matches the local session identity instead of assuming the
first record belongs to the local player. Stable-snapshot checks cover identity,
membership and definitions, excluding continuously changing cooldown timers.
No native game functions are called. Revision 8 is locally tested; its first
in-game validation is pending.

Revision 6 fixes premature SEAF Artillery export. It mirrors the supported
build's artillery eligibility check at `0x66CA6C`, with ammunition enumeration
also confirmed at `0xB56ECE`. Manager registry `+0x1CB8/+0x1CC0` identifies
controller type `0x65`; controller `+0xC` bounds its ammunition records,
`+0x50` points to records of stride `0x2C`, and `+0x38` holds unit pointers.
An enabled order (`+0x24 != 0xFFFFFFFF`), remaining ammunition (`+0 != 0`),
and a valid selected artillery unit are required. SEAF is omitted if its state
cannot be read. All fields participate in the stable-snapshot check.
Tests cover preloaded-but-disabled, enabled, depleted, invalid-unit and missing
controller states. Other contextual grants, including Hellbomb and Upload Data,
still require separate proximity/objective gates; this is a targeted SEAF fix.

Optional [ModOptionsMenu](https://github.com/CowboyBingus/ModOptionsMenu) settings
are registered under EquippedStratagems: Hide Stratagems on Cooldown (ON), Include
Mission Grants (ON), and Update Frequency (0.25/0.5/1 second, default 0.5).
Applied values are read through the v1 API; late dependency loading is supported.
Defaults also work without the options menu. Native cooldown evidence is at
`0x66D200` and HUD `0x1836510`: simulation clock `*(game+0x3326348)+0x18`,
entry cooldown `+0x18`, delivery `+0x20`, and Reinforce's shared mission `+0x50`.
Unsigned 64-bit timestamps are compared without floating-point conversion.

`EquippedStratagems.log` remains names-only. `EquippedStratagems_state.log` adds
a version, count and END marker for the updated wheel reader. A complete empty
snapshot clears the wheel; a partial concurrent read retains its previous valid
snapshot. The modern snapshot takes priority over legacy logs and bypasses the
wheel's unconditional Reinforce/Resupply additions. An open wheel refreshes every
250 ms; a membership change clears its selection until the pointer moves again.

## Repair

The original addon searched unrelated fields of the player manager for arrays
and expected English catalog names in binary definition records. The repair
reads the local selection card, verifies its identity against the local session
and its four slots against the player's payload, and checks that the snapshot
did not change during the read.

An in-game diagnostic also established that the old debug-name table address
was stale. Names now resolve from the selected definition's actual input code:
pointer at `StratagemInfo +0x40`, count at `+0x48`, and directions
`1=up, 2=right, 3=down, 4=left`. The 113 unambiguous code mappings come from
the supplied wheel project's catalog. The supported Upload Data definition
disambiguates its shared code from Reinforcement Pods. Unknown codes reject the entire export
and produce a diagnostic rather than a guessed or partial list.

The layout is limited to game.dll PE timestamp `1790161983`. Reads use the
existing in-process LuaJIT loader and Windows ReadProcessMemory. No game memory
is written. The local-selection layout was independently implemented using
the installed DiverKit alpha 8.10.1 reader as layout evidence.

Polling no longer depends on opening the Ctrl menu or on update receiving a
numeric time delta. Write, flush and close failures are checked and retried;
update chaining preserves the previous callback's return values. Diagnostics
go to `EquippedStratagems_diagnostics.log`, leaving the export names-only.

## Build and tests

Run with Python 3:

```text
python assemble.py
python build.py
python -m unittest discover -s tests -p "test_*.py"
python run_lua.py tests/runtime_test.lua
python run_lua.py tests/ffi_smoke.lua
```

`assemble.py` combines `common.lua`, `codes.lua`, `options.lua`, `eligibility.lua` and `runtime.lua` into the single
addon entry. The test runner loads the installed game's LuaJIT DLL into its own
test process, not into Helldivers. Its DLL path is configured in `run_lua.py`.
Fixtures cover local/remote identity, changing snapshots, zero/one/four slots,
automatic updates without dt, binding refresh, mission retention and clearing,
failed I/O retries, unsupported builds/codes, and callback chaining. A separate
package test verifies the resource envelope and that the ZIP contains the
current entry script.

The revision 3 live selection test captured all four user-confirmed choices in
order: Eagle 500kg Bomb, Orbital 120mm HE Barrage, Orbital Gatling Barrage and
AC-8 Autocannon. The observed IDs/codes are recorded in
`tests/fixtures/live-selection-r3.txt`.
After the user deployed and confirmed landing, the diagnostic reported
`mission=true`, `count=4`, and `source=cached selection`; the output file still
contained all four correct names. Selection capture and mission retention are
therefore verified in the installed game, in addition to the isolated tests.

Revision 7 adds Upload Data gating from native 0x6F24D0/0x6F3100.
Controller *(game+0x3326530) has count +0xC, config array +0x38 (stride 0x2C),
and state array +0x40 (stride 0x40). Config +0x26 is the game-maintained local
proximity result; prerequisite config/state flags are checked as well. No game
functions are called. This relies on the game updating its proximity cache;
refresh behavior with the stratagem menu closed still needs in-game verification.
Hellbomb and Eagle Rearm contextual gates remain outstanding.

Revision 8 gates Eagle Rearm by comparing remaining Eagle uses with their
maximum (including local-peer capacity upgrades), mirroring 0x66D650 and
0x879550. Full stock hides Rearm; spent uses expose it. Read failures omit
Rearm rather than guessing. Unit tests cover upgrades and replenishment;
in-game validation is pending. Hellbomb contextual gating remains outstanding.
