"""Fuzzy-match OCR lines to the stratagem table.

On-screen arrow glyphs win over the table when they parse as a clean code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from rapidfuzz import fuzz

from stratagems.arrows import merge_orphan_arrow_lines, split_name_and_arrows
from stratagems.catalog import STRATAGEMS, LoadoutEntry, Stratagem

_EXTRA_ALIASES: dict[str, tuple[str, ...]] = {
    "SoS Beacon": ("SOS Beacon", "SOS", "S.O.S. Beacon"),
    "Eagle 500kg Bomb": ("500kg", "500 kg", "Eagle 500KG Bomb", "500KG"),
    "NUX-223 Hellbomb": ("Hellbomb",),
    "Orbital Precision Strike": ("Precision Strike",),
    "StA-X3 W.A.S.P. Launcher": ("WASP Launcher", "W.A.S.P. Launcher"),
}

_THRESHOLD = 88.0
_MARGIN = 5.0


@dataclass(frozen=True)
class Match:
    stratagem: Stratagem
    score: float
    exact: bool


def short_alias(name: str) -> str | None:
    """Drop a leading weapon designation such as MG-43 or A/MG-43."""
    parts = name.split()
    if len(parts) < 2:
        return None
    first = parts[0]
    if any(char.isdigit() for char in first) or "/" in first:
        return " ".join(parts[1:])
    return None


def aliases(stratagem: Stratagem) -> tuple[str, ...]:
    names = [stratagem.name]
    short = short_alias(stratagem.name)
    if short and short.casefold() != stratagem.name.casefold():
        names.append(short)
    names.extend(_EXTRA_ALIASES.get(stratagem.name, ()))
    return tuple(names)


def normalize(text: str) -> str:
    folded = text.casefold()
    folded = folded.replace("w.a.s.p.", "wasp")
    folded = folded.replace("s.o.s.", "sos").replace("s.o.s", "sos")
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return re.sub(r"\s+", " ", folded).strip()


def best_match(
    query: str,
    entries: Sequence[Stratagem] | None = None,
) -> Match | None:
    raw = normalize(query)
    if not raw:
        return None
    folded = _fold_ocr(raw)
    forms = {raw, folded}
    pool = entries if entries is not None else STRATAGEMS

    full = [item for item in pool if normalize(item.name) in forms]
    if len(full) == 1:
        return Match(full[0], 100.0, True)
    if len(full) > 1:
        return None

    alias_hits: list[Stratagem] = []
    for stratagem in pool:
        for alias in aliases(stratagem):
            if alias.casefold() == stratagem.name.casefold():
                continue
            if normalize(alias) in forms:
                alias_hits.append(stratagem)
                break
    unique = _unique(alias_hits)
    if len(unique) == 1:
        return Match(unique[0], 100.0, True)
    if len(unique) > 1:
        return None

    if sum(char.isalpha() for char in raw) < 3:
        return None

    scored: list[tuple[float, Stratagem]] = []
    for stratagem in pool:
        best = 0.0
        for alias in aliases(stratagem):
            alias_n = normalize(alias)
            for form in forms:
                best = max(best, float(fuzz.ratio(form, alias_n)))
        scored.append((best, stratagem))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored or scored[0][0] < _THRESHOLD:
        return None
    if len(scored) > 1 and scored[0][0] - scored[1][0] < _MARGIN:
        return None
    return Match(scored[0][1], scored[0][0], False)


def resolve_line(line: str, entries: Sequence[Stratagem] | None = None) -> LoadoutEntry | None:
    name, arrows = split_name_and_arrows(line)
    match = best_match(name, entries) if name else None
    if arrows:
        if match is not None:
            return LoadoutEntry(match.stratagem.name, tuple(arrows), "screen")
        if sum(char.isalpha() for char in name) >= 4:
            return LoadoutEntry(name.strip(), tuple(arrows), "screen")
        return None
    if match is None:
        return None
    return LoadoutEntry(match.stratagem.name, match.stratagem.code, "table")


def resolve_lines(
    lines: list[str],
    entries: Sequence[Stratagem] | None = None,
) -> list[LoadoutEntry]:
    found: list[LoadoutEntry] = []
    seen: set[str] = set()
    for line in merge_orphan_arrow_lines(lines):
        row = resolve_line(line, entries)
        if row is None:
            continue
        key = row.name.casefold()
        if key in seen:
            continue
        seen.add(key)
        found.append(row)
    return found


def _fold_ocr(text: str) -> str:
    return text.replace("0", "o").replace("1", "l").replace("|", "l")


def _unique(items: list[Stratagem]) -> list[Stratagem]:
    seen: list[Stratagem] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen
