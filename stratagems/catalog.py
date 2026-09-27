"""Verified Helldivers 2 stratagem codes.

Source: The Helldivers Wiki, https://helldivers.wiki.gg/wiki/Stratagems
Each code is the infobox ``stratagem_code`` (``{{Stratagem_code|...}}``) on that
stratagem's wiki page, retrieved through the MediaWiki API on 2026-09-26.
Directions are published as up / down / left / right. Nothing here is invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CodeSource = Literal["screen", "table", "sample", "manual"]
MAX_WHEEL = 12

KIND_ORDER: tuple[str, ...] = (
    "Ship",
    "Orbital",
    "Eagle",
    "Support Weapon",
    "Backpack",
    "Vehicle",
    "Sentry",
    "Emplacement",
    "Objective",
    "Other",
)

SAMPLE_NAMES: tuple[str, ...] = (
    "Reinforce",
    "Resupply",
    "SoS Beacon",
    "Eagle Rearm",
    "Eagle Airstrike",
    "Eagle 500kg Bomb",
    "Orbital Precision Strike",
    "NUX-223 Hellbomb",
    "SEAF Artillery",
    "MG-43 Machine Gun",
)


@dataclass(frozen=True)
class Stratagem:
    name: str
    code: tuple[str, ...]
    kind: str
    permit: str


@dataclass(frozen=True)
class LoadoutEntry:
    name: str
    code: tuple[str, ...]
    code_source: CodeSource


def _s(name: str, code: str, kind: str, permit: str) -> Stratagem:
    return Stratagem(name, tuple(code.split()), kind, permit)


STRATAGEMS: tuple[Stratagem, ...] = (
    _s("Call In Super Destroyer", "up up down down left right left right", "Ship", ""),
    _s("Eagle Rearm", "up up left up right", "Ship", ""),
    _s("Reinforce", "up down right left up", "Ship", ""),
    _s("Resupply", "down down up right", "Ship", ""),
    _s("SoS Beacon", "up down right up", "Ship", "Supply"),
    _s("Orbital 120mm HE Barrage", "right right down left right down", "Orbital", "Offensive"),
    _s("Orbital 380mm HE Barrage", "right down up up left down down", "Orbital", "Offensive"),
    _s("Orbital Airburst Strike", "right right right", "Orbital", "Offensive"),
    _s("Orbital EMS Strike", "right right left down", "Orbital", "Offensive"),
    _s("Orbital Gas Strike", "right right down right", "Orbital", "Offensive"),
    _s("Orbital Gatling Barrage", "right down left up up", "Orbital", "Offensive"),
    _s("Orbital Laser", "right down up right down", "Orbital", "Offensive"),
    _s("Orbital Napalm Barrage", "right right down left right up", "Orbital", "Offensive"),
    _s("Orbital Precision Strike", "right right up", "Orbital", "Offensive"),
    _s("Orbital Railcannon Strike", "right up down down right", "Orbital", "Offensive"),
    _s("Orbital Smoke Strike", "right right down up", "Orbital", "Offensive"),
    _s("Orbital Walking Barrage", "right down right down right down", "Orbital", "Offensive"),
    _s("Eagle 110mm Rocket Pods", "up right up left", "Eagle", "Offensive"),
    _s("Eagle 500kg Bomb", "up right down down down", "Eagle", "Offensive"),
    _s("Eagle Airstrike", "up right down right", "Eagle", "Offensive"),
    _s("Eagle Cluster Bomb", "up right down down right", "Eagle", "Offensive"),
    _s("Eagle Gas Airstrike", "up right left right", "Eagle", "Offensive"),
    _s("Eagle Napalm Airstrike", "up right down up", "Eagle", "Offensive"),
    _s("Eagle Smoke Strike", "up right up down", "Eagle", "Offensive"),
    _s("Eagle Strafing Run", "up right right", "Eagle", "Offensive"),
    _s("40-K Meltagun", "down left up left left down", "Support Weapon", "Supply"),
    _s("AC-8 Autocannon", "down left down up up right", "Support Weapon", "Supply"),
    _s("APW-1 Anti-Materiel Rifle", "down left right up down", "Support Weapon", "Supply"),
    _s("ARC-3 Arc Thrower", "down right down up left left", "Support Weapon", "Supply"),
    _s("B/FLAM-80 Cremator", "down down right down up up", "Support Weapon", "Supply"),
    _s("B/MD C4 Pack", "down right up up right up", "Support Weapon", "Supply"),
    _s("CQC-1 One True Flag", "down left right right up", "Support Weapon", "Supply"),
    _s("CQC-20 Breaching Hammer", "down left right left up", "Support Weapon", "Supply"),
    _s("CQC-9 Defoliation Tool", "down left right right down", "Support Weapon", "Supply"),
    _s("EAT-17 Expendable Anti-Tank", "down down left up right", "Support Weapon", "Supply"),
    _s("EAT-411 Leveller", "down down left up down", "Support Weapon", "Supply"),
    _s("EAT-700 Expendable Napalm", "down down left up left", "Support Weapon", "Supply"),
    _s("FAF-14 Spear", "down down up down down", "Support Weapon", "Supply"),
    _s("FLAM-40 Flamethrower", "down left up down up", "Support Weapon", "Supply"),
    _s("GL-21 Grenade Launcher", "down left up left down", "Support Weapon", "Supply"),
    _s("GL-28 Belt-Fed Grenade Launcher", "down left up left up up", "Support Weapon", "Supply"),
    _s("GL-52 De-Escalator", "down right up left right", "Support Weapon", "Supply"),
    _s("GR-8 Recoilless Rifle", "down left right right left", "Support Weapon", "Supply"),
    _s("LAS-98 Laser Cannon", "down left down up left", "Support Weapon", "Supply"),
    _s("LAS-99 Quasar Cannon", "down down up left right", "Support Weapon", "Supply"),
    _s("M-1000 Maxigun", "down left right down up up", "Support Weapon", "Supply"),
    _s("M-105 Stalwart", "down left down up up left", "Support Weapon", "Supply"),
    _s("MG-206 Heavy Machine Gun", "down left up down down", "Support Weapon", "Supply"),
    _s("MG-43 Machine Gun", "down left down up right", "Support Weapon", "Supply"),
    _s("MGX-42 Bullet Storm", "down left down right up left", "Support Weapon", "Supply"),
    _s("MLS-4X Commando", "down left up down right", "Support Weapon", "Supply"),
    _s("MS-11 Solo Silo", "down up right down down", "Support Weapon", "Supply"),
    _s("PLAS-45 Epoch", "down left up left right", "Support Weapon", "Supply"),
    _s("RL-77 Airburst Rocket Launcher", "down up up left right", "Support Weapon", "Supply"),
    _s("RS-422 Railgun", "down right down up left right", "Support Weapon", "Supply"),
    _s("S-11 Speargun", "down right down left up right", "Support Weapon", "Supply"),
    _s("StA-X3 W.A.S.P. Launcher", "down down up down right", "Support Weapon", "Supply"),
    _s("TX-41 Sterilizer", "down left up down left", "Support Weapon", "Supply"),
    _s("AX/AR-23 Guard Dog", "down up left up right down", "Backpack", "Supply"),
    _s("AX/ARC-3 K-9", "down up left up right left", "Backpack", "Supply"),
    _s("AX/FLAM-75 Hot Dog", "down up left up left left", "Backpack", "Supply"),
    _s("AX/LAS-5 Rover", "down up left up right right", "Backpack", "Supply"),
    _s("AX/TX-13 Dog Breath", "down up left up right up", "Backpack", "Supply"),
    _s("B-1 Supply Pack", "down left down up up down", "Backpack", "Supply"),
    _s("B-100 Portable Hellbomb", "down right up up up", "Backpack", "Supply"),
    _s("LIFT-182 Warp Pack", "down left right down left right", "Backpack", "Supply"),
    _s("LIFT-850 Jump Pack", "down up up down up", "Backpack", "Supply"),
    _s("LIFT-860 Hover Pack", "down up up down left right", "Backpack", "Supply"),
    _s("SH-20 Ballistic Shield Backpack", "down left down down up left", "Backpack", "Supply"),
    _s("SH-32 Shield Generator Pack", "down up left right left right", "Backpack", "Supply"),
    _s("SH-51 Directional Shield", "down up left right up up", "Backpack", "Supply"),
    _s("EXO-45 Patriot Exosuit", "left down right up left down down", "Vehicle", "Supply"),
    _s("EXO-49 Emancipator Exosuit", "left down right up left down up", "Vehicle", "Supply"),
    _s("EXO-51 Lumberer Exosuit", "left down right up right left up", "Vehicle", "Supply"),
    _s("EXO-55 Breakthrough Exosuit", "left down right left right down up", "Vehicle", "Supply"),
    _s("M-102 Gunner FRV", "left down right down right down up", "Vehicle", "Supply"),
    _s("M-103 Supply FRV", "left down left left down up right", "Vehicle", "Supply"),
    _s("M-104 Incinerator FRV", "left down right left down up up", "Vehicle", "Supply"),
    _s("TD-110 Maelstrom", "left down right down left down up left right", "Vehicle", "Supply"),
    _s("TD-220 Bastion MK XVI", "left down right down left down up down up", "Vehicle", "Supply"),
    _s("A/AC-8 Autocannon Sentry", "down up right up left up", "Sentry", "Defensive"),
    _s("A/ARC-3 Tesla Tower", "down up right up left right", "Sentry", "Defensive"),
    _s("A/FLAM-40 Flame Sentry", "down up right down up up", "Sentry", "Defensive"),
    _s("A/G-16 Gatling Sentry", "down up right left", "Sentry", "Defensive"),
    _s("A/GM-17 Gas Mortar Sentry", "down up right down left", "Sentry", "Defensive"),
    _s("A/LAS-98 Laser Sentry", "down up right down up right", "Sentry", "Defensive"),
    _s("A/M-12 Mortar Sentry", "down up right right down", "Sentry", "Defensive"),
    _s("A/M-23 EMS Mortar Sentry", "down up right down right", "Sentry", "Defensive"),
    _s("A/MG-43 Machine Gun Sentry", "down up right right up", "Sentry", "Defensive"),
    _s("A/MLS-4X Rocket Sentry", "down up right right left", "Sentry", "Defensive"),
    _s("E/AT-12 Anti-Tank Emplacement", "down up left right right right", "Emplacement", "Defensive"),
    _s("E/GL-21 Grenadier Battlement", "down right down left right", "Emplacement", "Defensive"),
    _s("E/MG-101 HMG Emplacement", "down up left right right left", "Emplacement", "Defensive"),
    _s("FX-12 Shield Generator Relay", "down down left right left right", "Emplacement", "Defensive"),
    _s("MD-17 Anti-Tank Mines", "down left up up", "Emplacement", "Defensive"),
    _s("MD-6 Anti-Personnel Minefield", "down left up right", "Emplacement", "Defensive"),
    _s("MD-8 Gas Mines", "down left left right", "Emplacement", "Defensive"),
    _s("MD-I4 Incendiary Mines", "down left left down", "Emplacement", "Defensive"),
    _s("Activate E-711 Extraction Drill", "down down left left down down", "Objective", "Supply"),
    _s("Aquifer Drill", "left left left up down right down down", "Objective", ""),
    _s("Cargo Container", "up up down down right down", "Objective", ""),
    _s("Dark Fluid Vessel", "up left right down up up", "Objective", "Supply"),
    _s("Hive Breaker Drill", "left up down right down down", "Objective", ""),
    _s("NUX-223 Hellbomb", "down up left down up right down up", "Objective", ""),
    _s("Portable Comms Relay", "up up down down left left down", "Objective", ""),
    _s("Prospecting Drill", "down down left right down down", "Objective", ""),
    _s("Reinforcement Pods", "left right up up up", "Objective", ""),
    _s("SEAF Artillery", "right up up down", "Objective", ""),
    _s("Seismic Probe", "up up left right down down", "Objective", ""),
    _s("SSSD Delivery", "down down down down down up up", "Objective", ""),
    _s("Super Earth Flag", "down up down up", "Objective", ""),
    _s("Tactical Video Camera", "right down down up left left up", "Objective", "Supply"),
    _s("Tectonic Drill", "up down up down up down", "Objective", "Supply"),
    _s("Upload Data", "left right up up up", "Objective", ""),
    _s("Orbital Illumination Flare", "right right left left", "Other", ""),
)

BY_NAME: dict[str, Stratagem] = {item.name: item for item in STRATAGEMS}


def get(name: str) -> Stratagem | None:
    return BY_NAME.get(name)


def sample_loadout() -> tuple[Stratagem, ...]:
    return tuple(BY_NAME[name] for name in SAMPLE_NAMES)


def grouped() -> list[tuple[str, tuple[Stratagem, ...]]]:
    buckets: dict[str, list[Stratagem]] = {}
    for item in STRATAGEMS:
        buckets.setdefault(item.kind, []).append(item)
    ordered: list[tuple[str, tuple[Stratagem, ...]]] = []
    seen: set[str] = set()
    for kind in KIND_ORDER:
        if kind in buckets:
            ordered.append((kind, tuple(buckets[kind])))
            seen.add(kind)
    for kind, items in buckets.items():
        if kind not in seen:
            ordered.append((kind, tuple(items)))
    return ordered
