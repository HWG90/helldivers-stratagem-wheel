# Helldivers 2 stratagem wheel

A desktop tool that reads the stratagem list on your screen, puts those stratagems on a radial wheel, and types the arrow code with ordinary keypresses.

It does not attach to the game. There is no process injection, no memory reading, no game hook, and no attempt to hide the tool. Capture is a rectangle you draw (`mss`, with a Pillow screenshot fallback when a display rejects `mss`). Input is a normal key-down / key-up stream, the same class of event a macro pad sends.

> **Anti-cheat and terms.** Helldivers 2 ships with anti-cheat, and its terms can treat macros as cheating. This program does not bypass GameGuard, nProtect, or any other anti-cheat, and it does not hide itself. Those systems can still flag simulated input and can suspend or ban an account. If you point this at the live game, you accept that risk. `--demo` never sends keystrokes.

Primary target is Windows, where the game runs. `--demo` and the unit tests run on Linux.

## Install

Python 3.11 or newer.

```bash
python -m venv .venv
```

Windows:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
```

Install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) and make sure `tesseract` is on `PATH`.

Linux (demo and tests):

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

Hold the radial bind. The wheel opens at the cursor. Move onto a wedge and release to type that stratagem. Release over the center, or press Escape, to cancel.

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
4. Leave **Auto-scan** on. The next time you hold the radial bind, that rectangle is captured and read.

**RESCAN NOW**, or the rescan bind (Mouse4), reads the region again without waiting for the wheel.

Matching uses the verified code table below. If the arrow glyphs on a row parse as a clean direction run, those on-screen arrows are used instead of the table. If they do not (the in-game arrows are often custom art, and Tesseract may not see them as arrow characters), the table code is used.

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

The tests cover sequence timing, fuzzy name matching, arrow-glyph parsing, and angle-to-wedge selection. They do not need the game.

## What this will not do

No injection into the game process, no memory reads, no hooks inside the game, no anti-cheat bypass, and no hidden process. If global mouse and keyboard listening is blocked on your machine, the preview wheel and the dry-run panel still work; live typing will not, and the terminal says so.
