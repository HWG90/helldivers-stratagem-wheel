"""Read the equipped-stratagem log written beside the shared loader logs.

Bingus Shared Loader and Mod Bindings Menu do not write StratagemSlots.log.
That file is still checked first, in case a loadout list is already there.
When it has no catalog names, the wheel reads the sibling EquippedStratagems.log.
"""

from __future__ import annotations

import os
from pathlib import Path

from stratagems.catalog import STRATAGEMS, LoadoutEntry, Stratagem
from stratagems.matching import aliases, normalize

SLOTS_LOG_NAME = "StratagemSlots.log"
EQUIPPED_LOG_NAME = "EquippedStratagems.log"
LOG_NAMES = (SLOTS_LOG_NAME, EQUIPPED_LOG_NAME)


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
