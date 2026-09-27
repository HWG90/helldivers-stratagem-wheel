# Helldivers 2 stratagem wheel

A desktop tool that reads the stratagem list on your screen, puts those stratagems on a radial wheel, and types the arrow code with ordinary keypresses.

It does not attach to the game. There is no process injection, no memory reading, no game hook, and no attempt to hide the tool. Capture is a rectangle you draw (`mss`, with a Pillow screenshot fallback when a display rejects `mss`). Input is a normal key-down / key-up stream, the same class of event a macro pad sends.

> **Anti-cheat and terms.** Helldivers 2 ships with anti-cheat, and its terms can treat macros as cheating. This program does not bypass GameGuard, nProtect, or any other anti-cheat, and it does not hide itself. Those systems can still flag simulated input and can suspend or ban an account. If you point this at the live game, you accept that risk. `--demo` never sends keystrokes.

Primary target is Windows, where the game runs. `--demo` and the unit tests run on Linux.

## Run on Windows

Double-click `Start.bat` in this folder.

- If `HelldiversStratagemWheel.exe` is beside `Start.bat`, that file starts.
- Otherwise `Start.bat` creates a virtual environment, installs `requirements.txt`, and runs `python -m stratagems`. A scan reads arrow shapes when they classify, and otherwise reads names with Windows.Media.Ocr, then RapidOCR, then Tesseract.
- Or download `HelldiversStratagemWheel.exe` from the Windows exe workflow and double-click it. GitHub runs `.github/workflows/windows-exe.yml`. Origin runs `.depot/workflows/windows-exe.yml`.

## Windows

Download `HelldiversStratagemWheel.exe` and double-click it. Python does not need to be installed.

The first launch unpacks a private runtime under `%LOCALAPPDATA%\HelldiversStratagemWheel` and opens Stratagem Terminal in live mode. Hold **Mouse3** to open the wheel. **Mouse4** scans the list once for the mission. Later launches reuse that folder when the bundled version has not changed.

Arrow codes are matched by shape when the glyphs classify. Otherwise the packaged app reads names with Windows.Media.Ocr, then RapidOCR (ONNX). If both return nothing and the crop still looks like text, it uses the bundled Tesseract and `eng.traineddata`. A scan that finds nothing says why in the terminal. Opening the wheel does not scan.

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

Linux (demo and tests) still uses Tesseract when a name has to be read:

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
| Rescan the list | **Mouse4** |
| Stratagem modifier | **Left Control** |
| Direction keys | Arrow keys |
| Cancel | Release in the center deadzone, or **Escape** |

Hold the radial bind. The wheel opens at the center of the monitor that contains the cursor and stays there until you release. It shows the last successful scan. It does not capture the screen. Press the scan bind (Mouse4 by default), or **SCAN** in the terminal, to read the calibrated region once. That loadout stays until the next press. The OS cursor hides while the wheel bind is held. Aim with the mouse: each movement is added to a virtual offset from the spot where you pressed, and the cursor is warped back there so a game camera does not spin. A line on the wheel runs from the center to a dot at that offset. The line grows toward the highlighted wedge and shrinks back to the center inside the deadzone. The dot stays on the wheel; the wedge still uses the real offset. That line is the only aim indicator. Release outside the center deadzone to type that stratagem. Release inside the deadzone, or press Escape, to cancel. Releasing shows the cursor again on the saved spot.

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

## Calibrate OCR

Until a region is saved, the wheel shows **NOT CALIBRATED — SAMPLE LOADOUT** and a built-in sample (Reinforce, Resupply, SoS Beacon, Eagle Rearm, Eagle Airstrike, Eagle 500kg Bomb, Orbital Precision Strike, Hellbomb, SEAF Artillery, Machine Gun). You can use that wheel immediately.

To read the list from the game:

1. Open the stratagem menu in Helldivers 2 so the names and arrow codes are on screen.
2. In Stratagem Terminal, click **CALIBRATE**.
3. Drag a rectangle around that list, including each name and its arrows. Save.
4. Press the scan bind (Mouse4) or click **SCAN**. That reads the rectangle once and stores the loadout for the mission.

**SCAN**, or the scan bind, reads that region once. Opening the wheel does not. The HDR preview uses that same capture, or a new one when you click **AUTO** or release a slider. It does not keep capturing while the window is open, and it does not replace the saved loadout.

### Windows HDR

An HDR desktop can hand that same rectangle back flat, dark, or blown out. Under **HDR**, next to the region controls, turn on **Adjust captures before reading**. The preview shows each segmented arrow glyph and the direction the matcher chose. The curve, when HDR is on, is applied before that segmentation. The image updates when you scan, click **AUTO**, or release a slider. It does not refresh on a timer. **AUTO** sets exposure, gamma, contrast, and black level from one crop's histogram. Move the sliders if a glyph is still soft. The toggle and the four values are saved in the config file.

A scan keeps an arrow code only when the glyphs classify above the confidence threshold. Real Helldivers arrows are not required to match the synthetic triangle templates. If they do not, the same capture is read as names: Windows.Media.Ocr, then RapidOCR, then Tesseract when the crop still contains text. The catalog supplies the code for a recognized name. Samples of each direction are stored after an arrow hit and reused on the next scan. If two stratagems share a code, an icon patch stored from an earlier recognition breaks the tie. A scan that finds nothing leaves the last loadout in place when there is one, and the terminal says whether the capture had no rows, low arrow confidence, or no text. The HDR preview still updates only when you scan, click **AUTO**, or release a slider.

The wheel shows up to 12 stratagems, which covers a normal loadout plus mission stratagems.

## Manual loadout

Turn on **Manual override**, then pin stratagems from the checklist. The wheel uses that list and skips OCR. Pin order is the order you check them. Past 12, the wheel keeps the first 12.

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

The tests cover sequence timing, fuzzy name matching, arrow-shape codes, the aim line staying on the wheel, hiding the cursor for a hold, centering the wheel on the monitor under the cursor, summing mouse deltas across a cursor warp, and that opening the wheel does not scan. They do not need the game.

## What this will not do

No injection into the game process, no memory reads, no hooks inside the game, no anti-cheat bypass, and no hidden process. If global mouse and keyboard listening is blocked on your machine, the preview wheel and the dry-run panel still work; live typing will not, and the terminal says so.
