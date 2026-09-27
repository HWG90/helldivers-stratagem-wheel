# Helldivers 2 stratagem wheel

A desktop tool that reads the stratagem list on your screen, puts those stratagems on a radial wheel, and types the arrow code with ordinary keypresses.

It does not attach to the game. There is no process injection, no memory reading, no game hook, and no attempt to hide the tool. Capture is a rectangle you draw (`mss`, with a Pillow screenshot fallback when a display rejects `mss`). Input is a normal key-down / key-up stream, the same class of event a macro pad sends.

> **Anti-cheat and terms.** Helldivers 2 ships with anti-cheat, and its terms can treat macros as cheating. This program does not bypass GameGuard, nProtect, or any other anti-cheat, and it does not hide itself. Those systems can still flag simulated input and can suspend or ban an account. If you point this at the live game, you accept that risk. `--demo` never sends keystrokes.

Primary target is Windows, where the game runs. `--demo` and the unit tests run on Linux.

## Run on Windows

Double-click `Start.bat` in this folder.

- If `HelldiversStratagemWheel.exe` is beside `Start.bat`, that file starts.
- Otherwise `Start.bat` creates a virtual environment, installs `requirements.txt`, and runs `python -m stratagems`. Learn tags arrow shapes from your screen. Scan matches those saved shapes. It does not call an OCR engine.
- Or download `HelldiversStratagemWheel.exe` from the Windows exe workflow and double-click it. GitHub runs `.github/workflows/windows-exe.yml`. Origin runs `.depot/workflows/windows-exe.yml`.

## Windows

Download `HelldiversStratagemWheel.exe` and double-click it. Python does not need to be installed.

The first launch unpacks a private runtime under `%LOCALAPPDATA%\HelldiversStratagemWheel` and opens Stratagem Terminal in live mode. Hold **Mouse3** to open the wheel. **Mouse5** learns arrow shapes. **Mouse4** scans the list once for the mission. Later launches reuse that folder when the bundled version has not changed.

A scan compares each arrow glyph to the shapes saved by Learn. It does not call Windows OCR, RapidOCR, or Tesseract. With no samples saved, it tells you to run Learn and leaves the loadout alone. A glyph that matches nothing names the row and keeps the previous loadout. Opening the wheel does not scan.

The file is unsigned. SmartScreen may ask you to confirm it.

Live mode still types real keypresses. The anti-cheat warning at the top applies to this download the same way it applies to a source checkout.

### How the exe was built

`scripts/build_windows_exe.sh` produces it on Linux. PyInstaller cannot cross-compile a Windows binary, so the script uses pynsist and NSIS:

1. pynsist downloads the official Windows embeddable CPython 3.12 (64-bit) and the Windows wheels for the Python dependencies.
2. That embeddable zip does not include tkinter. The script adds `_tkinter.pyd`, `tcl86t.dll`, `tk86t.dll`, and the `tkinter` package from the matching official Windows build (`tcltk.msi` on python.org).
3. It unpacks the UB Mannheim Tesseract 5.4 installer, keeps `tesseract.exe`, the DLLs it imports, and `tessdata/eng.traineddata`, and strips debug data out of those binaries.
4. NSIS (`makensis`) packs those folders into one PE executable. Double-clicking it extracts the runtime and starts `pythonw` on the launcher script. That script calls `stratagems.app:main` with no `--demo` flag, so the terminal listens for the radial bind.

The executable is a build product. It is not committed.

## Install from source

Python 3.11 or newer. The Windows exe above is the way to run it without installing Python. A source checkout is for development and for the Linux demo.

```bash
python -m venv .venv
```

Windows:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux (demo and tests) can still run Tesseract for the standalone line reader. A mission scan does not call it:

```bash
source .venv/bin/activate
pip install -r requirements.txt
sudo apt install tesseract-ocr python3-tk python3-dev
```

`python3-dev` is only there so `pynput` can build its Linux input dependency when a wheel is not available.

## Run

Demo, with a sample loadout. Sequences are printed and written in the terminal window. Nothing is typed into other programs:

```bash
python -m stratagems --demo
```

Live mode, after you have accepted the anti-cheat risk:

```bash
python -m stratagems
```

The settings window is a normal window titled Stratagem Terminal. The wheel is a separate frameless window that stays above other windows only while you are holding the radial bind.

## Default binds

| Action | Default |
| --- | --- |
| Open the wheel | Hold **Mouse3** (middle mouse) |
| Learn arrow shapes | **Mouse5** |
| Rescan the list | **Mouse4** |
| Stratagem modifier | **Left Control** |
| Direction keys | Arrow keys |
| Cancel | Release in the center deadzone, or **Escape** |

Hold the radial bind while Helldivers 2 is the focused window. The wheel stays closed in any other program, including this terminal. It opens at the center of the monitor that contains the cursor and stays there until you release. If the game loses focus during the hold, the wheel closes without typing a code. Preview in the terminal still opens the wheel on its own. Reinforce and Resupply are always on it, using the catalog codes, before any scan. A scan adds the rest of the mission loadout and does not list those two twice. Opening the wheel does not capture the screen. Press the scan bind (Mouse4 by default), or **SCAN** in the terminal, to match the calibrated region once against the shapes Learn saved. That loadout stays until the next press. The OS cursor hides while the wheel bind is held, including over the wheel itself, and comes back on release. On Windows the wheel is a borderless topmost layered window with no taskbar button and no focus steal. It does not hit-test the mouse, so the pointer does not turn into an arrow inside that rectangle. Aiming stays on the global listener and the drawn line. Aim with the mouse: each movement is added to a virtual offset from the spot where you pressed, and the cursor is warped back there so a game camera does not spin. The warp's own mouse event is ignored. A line on the wheel runs from the center to a dot at that offset, clamped to the wheel radius. Moving back toward the center shortens the stored offset, so the line shrinks. Inside the deadzone the line is short. The dot stays on the wheel; the wedge still uses the real offset. That line is the only aim indicator. Release outside the center deadzone to type that stratagem. Release inside the deadzone, or press Escape, to cancel. Releasing shows the cursor again on the saved spot.

**Transparent wheel** is off by default. When it is on, each wedge keeps its yellow outline and the fill is see-through. The backing, the gaps, and the hazard frame use a transparent color key. The title, the status banner, and the bottom hint are not drawn. Wedge labels, the center readout, and the aim line stay. Scan notes stay in the terminal, not on the wheel.

Rebind from the terminal: click REBIND, then press Mouse3, Mouse4, Mouse5, or any keyboard key. Escape cancels the capture. The new bind is written immediately.

Direction keys can be switched to WASD. The stratagem modifier can be another key if you have rebound the stratagem menu in the game.

## Timing

The live sequence holds the modifier, taps each direction, then releases the modifier.

| Setting | Default | Meaning |
| --- | --- | --- |
| Delay before first direction | 80 ms | Wait after the modifier goes down |
| Gap between directions | 50 ms | Wait after one direction is released, before the next press |
| Tail before modifier release | 40 ms | Wait after the last direction is released |
| Direction key hold | 20 ms | How long each arrow or WASD key stays down |

Those defaults are a human-speed cadence a game sample can register. Raise them if a code drops inputs. Lower them only if the game is already accepting faster manual input.

The DRY RUN section prints the exact timestamps and keys for any stratagem in the table. It does not type them.

## Learn and scan

The wheel always shows **Reinforce** and **Resupply** from the catalog. You can call those in before any scan or Learn. A scan adds the other stratagems it reads. If that list also contains Reinforce or Resupply, each name appears once.

## Equipped loadout file

The wheel can take the mission loadout from a text file instead of a screen scan. The file is one stratagem name per line. Reinforce and Resupply stay on the wheel, and a name that is already there is not listed twice. A missing or empty file leaves Learn and Scan working. Manual override still uses the pinned list.

Bingus Shared Loader and Mod Bindings Menu do not write `StratagemSlots.log`. The wheel still reads that file when it already lists catalog names. Otherwise it reads the log **EquippedStratagems** writes:

`%LOCALAPPDATA%\CowboyBingus\Helldivers2\Logs\EquippedStratagems.log`

EquippedStratagems is a normal disclosed Helldivers 2 mod. Bingus Shared Loader discovers `mods/EquippedStratagems/EquippedStratagems`. On each update it writes catalog names, one per line, and rewrites the log when that list changes. A list that matches nothing leaves the previous file alone. An empty known list clears the file.

The first update creates the log even when no names are known yet. Until then the file is three status lines, each starting with `#` so the wheel skips them: whether `mods/codex/loadouts` had a usable name list (`no`; that addon is a compiled patch and is not called), whether `game.dll` was found, and the stratagem row count. When an in-mission loadout resolves, those lines are replaced by one catalog name per line.

Names are read only while mission mode is 1..7 (`*(game+0x33266a0)`, the same gate the other mods use). The ship menu is not the loadout. `game.dll` is `tonumber(GetModuleHandleA("game.dll"))`, and each read is `ReadProcessMemory` of that address. StratagemInfo is `*(game+0x348e8f8)` with the kind table at `game+0x37cb600`. Equipped rows are `*(game+0x33266b0)` (count at `+0x34`, stride 64, kind at `+12`). It does not patch code or hide itself.

It also registers a Mod Bindings Menu binding with `ModBindingsMenu.register_binding('equippedstratagems.send_strategems', 'Send Strategems', nil, {category = 'EquippedStratagems'})`. When **Send Strategems** fires, the same read runs and the log is written. The saved key lives in Mod Bindings Menu's own assignment table. Set the key on the MODS tab. The stratagem wheel program itself still does not attach to the game.

Install EquippedStratagems next to the loader, with Arsenal or HD2MM:

1. Close Helldivers 2. Use one mod manager.
2. Import [Bingus Shared Loader v15 or newer](https://github.com/CowboyBingus/BingusSharedLoader/releases/latest) (v18 is the current API 1 release), [Mod Bindings Menu v2](https://github.com/CowboyBingus/ModBindingsMenu/releases/latest), and `mods/EquippedStratagems/EquippedStratagems.zip` from this project.
3. Enable all three. With Arsenal's default priority, put **Bingus Shared Loader last**. If first-mod priority is on, put the loader first.
4. Purge / Deploy, then launch the game normally.
5. Check `%LOCALAPPDATA%\CowboyBingus\Helldivers2\Logs\BingusSharedLoader.log` for `mods/EquippedStratagems/EquippedStratagems: loaded`.
6. Open Options, then Mouse & Keyboard or Controller, and bind **Send Strategems** on the MODS tab.
7. Open the stratagem wheel. Names in the log fill it. If neither log has catalog names, use Learn and Scan as below.

The same steps are in `mods/EquippedStratagems/INSTALL.txt`, and that file is packed at the root of the zip. Rebuild the zip after editing the Lua entry:

```bash
python mods/EquippedStratagems/build.py
```

The package GUID stays `7f3a9c2e-6b14-4d58-8e21-0c5b9a4d71f6`. The resource name is `mods/EquippedStratagems/EquippedStratagems`. The source file sits at `mods/EquippedStratagems/EquippedStratagems.lua`, which is the layout the loader documents for an addon entry.

To read the list from the game:

1. Open the stratagem menu in Helldivers 2 so the arrow codes are on screen.
2. In Stratagem Terminal, click **CALIBRATE**.
3. Drag a rectangle around that list, including each row of arrows. Save.
4. Press **Mouse5** or click **LEARN**. Each unique arrow shape is shown. Tag it Up, Down, Left, or Right. Save. Those patches are stored in the config file.
5. Press the scan bind (Mouse4) or click **SCAN**. That matches every glyph to the saved patches and maps the code through the catalog.

**SCAN**, or the scan bind, reads that region once. Opening the wheel does not. If no samples are saved, the scan tells you to run Learn and does not guess. A glyph that matches nothing is skipped. Each remaining row is looked up on its own, and a row that does not match does not drop the others. The HDR preview uses the scan capture, or a new one when you click **AUTO** or release a slider. It does not keep capturing while the window is open, and it does not replace the saved loadout.

### Windows HDR

An HDR desktop can hand that same rectangle back flat, dark, or blown out. Under **HDR**, next to the region controls, turn on **Adjust captures before reading**. The preview shows each segmented arrow glyph and the direction the matcher chose. The curve, when HDR is on, is applied before that segmentation. The image updates when you scan, click **AUTO**, or release a slider. It does not refresh on a timer. **AUTO** sets exposure, gamma, contrast, and black level from one crop's histogram. Move the sliders if a glyph is still soft. The toggle and the four values are saved in the config file.

Learn segments glyphs after the HDR curve when HDR is on. A scan classifies every glyph by normalized comparison to the patches you tagged. A shape that matches nothing is skipped. Each row is read on its own, left to right. If those arrows contain a catalog code, the longest one is imported, and the scan keeps going through the rest of the list. A row with no matching arrows is skipped. The previous loadout stays only when the whole scan resolves nothing. It does not call an OCR engine, and it does not guess a direction from triangle geometry. If two stratagems share a code, an icon patch stored from an earlier sample match breaks the tie. A scan that finds nothing leaves the last loadout in place when there is one. The HDR preview still updates only when you scan, click **AUTO**, or release a slider. It does not refresh on a timer.

The wheel shows up to 12 stratagems, which covers a normal loadout plus mission stratagems.

## Manual loadout

Turn on **Manual override**, then pin stratagems from the checklist. The wheel uses that list and skips the scan. Reinforce and Resupply stay on the wheel. Pin order follows them. Past 12 names, the wheel keeps the first 12.

## Config

JSON is stored in the platform user config directory:

- Windows: `%APPDATA%\helldivers-stratagems\config.json`
- Linux and macOS: `$XDG_CONFIG_HOME/helldivers-stratagems/config.json` or `~/.config/helldivers-stratagems/config.json`

A broken file is moved aside and the defaults are loaded.

## Stratagem codes

Codes come from The Helldivers Wiki, [Stratagems](https://helldivers.wiki.gg/wiki/Stratagems). Each entry is the `stratagem_code` on that stratagem's infobox (`{{Stratagem_code|up|down|...}}`), retrieved through the MediaWiki API on 2026-09-26. The table includes orbital strikes, eagle strikes, support weapons, backpacks, vehicles, sentries, emplacements, and mission stratagems (Reinforce, Resupply, SoS Beacon, Hellbomb, SEAF Artillery, Eagle Rearm, and the rest of the published list).

Game patches change codes. If a code fails in game, check the wiki page before trusting a stale table. The source note is also at the top of `stratagems/catalog.py`.

## Tests

```bash
pip install pytest
pytest
```

The tests cover sequence timing, fuzzy name matching, learned arrow samples (including a thick chevron), the aim line shrinking inside the deadzone, hiding the cursor for a hold, centering the wheel on the monitor under the cursor, summing mouse deltas across a cursor warp, and that opening the wheel does not scan. They do not need the game.

## What this will not do

No injection into the game process, no memory reads, no hooks inside the game, no anti-cheat bypass, and no hidden process. If global mouse and keyboard listening is blocked on your machine, the preview wheel and the dry-run panel still work; live typing will not, and the terminal says so.
