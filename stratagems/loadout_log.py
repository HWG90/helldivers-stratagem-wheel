"""Read the equipped-stratagem log written beside the shared loader logs.

Bingus Shared Loader and Mod Bindings Menu do not write StratagemSlots.log.
That file is still checked first, in case a loadout list is already there.
When it has no catalog names, the wheel reads the sibling EquippedStratagems.log.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from stratagems.catalog import STRATAGEMS, LoadoutEntry, Stratagem
from stratagems.matching import aliases, normalize

SLOTS_LOG_NAME = "StratagemSlots.log"
EQUIPPED_LOG_NAME = "EquippedStratagems.log"
LOG_NAMES = (SLOTS_LOG_NAME, EQUIPPED_LOG_NAME)
STATE_LOG_NAME = "EquippedStratagems_state.log"


@dataclass
class LiveSnapshot:
    # None means a concurrent/incomplete read: retain the last complete snapshot.
    entries: list[LoadoutEntry] | None


def read_live_loadout() -> LiveSnapshot | None:
    """Read the authoritative framed export; None means no modern exporter."""
    directory = logs_directory()
    if directory is None:
        return None
    try:
        text = (directory / STATE_LOG_NAME).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError):
        return LiveSnapshot(None)
    lines = text.splitlines()
    if len(lines) < 3 or lines[0] != "EquippedStratagems snapshot 1" or lines[-1] != "END" or not text.endswith("\n"):
        return LiveSnapshot(None)
    try:
        count = int(lines[1].removeprefix("count="))
    except ValueError:
        return LiveSnapshot(None)
    if not lines[1].startswith("count=") or not 0 <= count <= 32 or len(lines) != count + 3:
        return LiveSnapshot(None)
    entries: list[LoadoutEntry] = []
    seen: set[str] = set()
    for name in lines[2:-1]:
        item = _resolve_name(name)
        if item is None or item.name in seen:
            return LiveSnapshot(None)
        seen.add(item.name)
        entries.append(LoadoutEntry(item.name, item.code, "table"))
    return LiveSnapshot(entries)


def logs_directory() -> Path | None:
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        return None
    return Path(root) / "CowboyBingus" / "Helldivers2" / "Logs"


def equipped_log_path() -> Path | None:
    directory = logs_directory()
    if directory is None:
        return None
    return directory / EQUIPPED_LOG_NAME


def _resolve_name(line: str) -> Stratagem | None:
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None
    folded = normalize(raw)
    if not folded:
        return None
    hits: list[Stratagem] = []
    for item in STRATAGEMS:
        forms = {normalize(item.name)}
        forms.update(normalize(alias) for alias in aliases(item))
        if folded in forms:
            hits.append(item)
    if len(hits) == 1:
        return hits[0]
    return None


def names_in_log(path: Path) -> list[LoadoutEntry] | None:
    """Catalog rows in this file, or None when the file is missing or empty of names."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return None
    if text.startswith("\ufeff"):
        text = text[1:]
    entries: list[LoadoutEntry] = []
    seen: set[str] = set()
    for line in text.splitlines():
        chosen = _resolve_name(line)
        if chosen is None:
            continue
        key = chosen.name.casefold()
        if key in seen:
            continue
        seen.add(key)
        entries.append(LoadoutEntry(chosen.name, chosen.code, "table"))
    if not entries:
        return None
    return entries


def read_logged_loadout() -> list[LoadoutEntry] | None:
    """The first log in this folder that lists catalog stratagems."""
    directory = logs_directory()
    if directory is None:
        return None
    for name in LOG_NAMES:
        found = names_in_log(directory / name)
        if found:
            return found
    return None


def recognition_block_reason(fallback_enabled: bool, manual_override: bool = False) -> str | None:
    """One policy for scan, learn, and shape previews. Logs always win."""
    if manual_override:
        return "Manual override is on; recognition is skipped."
    if read_live_loadout() is not None or read_logged_loadout():
        return "Live log mode is active; OCR and shape recognition are skipped."
    if not fallback_enabled:
        return "Live log mode is the default. Enable OCR / shape fallback in Loadout Source to scan without a log."
    return None
