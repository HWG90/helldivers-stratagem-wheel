"""JSON config in the platform user config directory."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from stratagems.catalog import BY_NAME
from stratagems.glyphs import sanitize_glyph_lut, sanitize_icon_lut
from stratagems.sequence import DirectionStyle


@dataclass
class Region:
    left: int
    top: int
    width: int
    height: int

    def to_dict(self) -> dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class Config:
    radial_bind: str = "mouse3"
    rescan_bind: str = "mouse4"
    learn_bind: str = "mouse5"
    modifier: str = "ctrl_l"
    direction_style: DirectionStyle = "arrows"
    start_delay_ms: int = 80
    gap_ms: int = 50
    tail_ms: int = 40
    tap_ms: int = 20
    manual_override: bool = False
    transparent_wheel: bool = False
    pinned: list[str] = field(default_factory=list)
    region: Region | None = None
    hdr: bool = False
    hdr_exposure: float = 0.0
    hdr_gamma: float = 1.0
    hdr_contrast: float = 1.0
    hdr_black_level: float = 0.0
    glyph_lut: dict[str, list[str]] = field(default_factory=dict)
    icon_lut: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": 1,
            "radial_bind": self.radial_bind,
            "rescan_bind": self.rescan_bind,
            "learn_bind": self.learn_bind,
            "modifier": self.modifier,
            "direction_style": self.direction_style,
            "start_delay_ms": self.start_delay_ms,
            "gap_ms": self.gap_ms,
            "tail_ms": self.tail_ms,
            "tap_ms": self.tap_ms,
            "manual_override": self.manual_override,
            "transparent_wheel": self.transparent_wheel,
            "pinned": list(self.pinned),
            "region": None if self.region is None else self.region.to_dict(),
            "hdr": self.hdr,
            "hdr_exposure": self.hdr_exposure,
            "hdr_gamma": self.hdr_gamma,
            "hdr_contrast": self.hdr_contrast,
            "hdr_black_level": self.hdr_black_level,
            "glyph_lut": {key: list(value) for key, value in self.glyph_lut.items()},
            "icon_lut": dict(self.icon_lut),
        }


def config_dir() -> Path:
    if sys.platform == "win32":
        root = os.environ.get("APPDATA")
        base = Path(root) if root else Path.home() / "AppData" / "Roaming"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "helldivers-stratagems"


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> tuple[Config, str | None]:
    path = config_path()
    if not path.exists():
        return Config(), None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        backup = path.with_suffix(".corrupt.json")
        try:
            path.replace(backup)
        except OSError:
            backup = path
        return Config(), f"Config could not be read ({exc}). Started from defaults. Kept {backup}."
    if not isinstance(data, dict):
        return Config(), "Config was not an object. Started from defaults."
    return _from_dict(data), None


def save_config(config: Config) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(config.to_dict(), indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def _from_dict(data: dict[str, object]) -> Config:
    style = data.get("direction_style")
    direction_style: DirectionStyle = "wasd" if style == "wasd" else "arrows"
    region = _region(data.get("region"))
    pinned = data.get("pinned")
    names = [name for name in pinned if isinstance(name, str) and name in BY_NAME] if isinstance(pinned, list) else []
    return Config(
        radial_bind=_text(data.get("radial_bind"), "mouse3"),
        rescan_bind=_text(data.get("rescan_bind"), "mouse4"),
        learn_bind=_text(data.get("learn_bind"), "mouse5"),
        modifier=_text(data.get("modifier"), "ctrl_l"),
        direction_style=direction_style,
        start_delay_ms=_ms(data.get("start_delay_ms"), 80),
        gap_ms=_ms(data.get("gap_ms"), 50),
        tail_ms=_ms(data.get("tail_ms"), 40),
        tap_ms=_ms(data.get("tap_ms"), 20),
        manual_override=_bool(data.get("manual_override"), False),
        transparent_wheel=_bool(data.get("transparent_wheel"), False),
        pinned=names,
        region=region,
        hdr=_bool(data.get("hdr"), False),
        hdr_exposure=_unit(data.get("hdr_exposure"), 0.0, -4.0, 4.0),
        hdr_gamma=_unit(data.get("hdr_gamma"), 1.0, 0.2, 3.0),
        hdr_contrast=_unit(data.get("hdr_contrast"), 1.0, 0.25, 3.0),
        hdr_black_level=_unit(data.get("hdr_black_level"), 0.0, 0.0, 0.95),
        glyph_lut=sanitize_glyph_lut(data.get("glyph_lut")),
        icon_lut=sanitize_icon_lut(data.get("icon_lut")),
    )


def _region(value: object) -> Region | None:
    if not isinstance(value, dict):
        return None
    try:
        left = int(value["left"])
        top = int(value["top"])
        width = int(value["width"])
        height = int(value["height"])
    except (KeyError, TypeError, ValueError):
        return None
    if width < 1 or height < 1:
        return None
    return Region(left, top, width, height)


def _text(value: object, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip().lower()
    return default


def _ms(value: object, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(0, min(2000, int(value)))


def _bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _unit(value: object, default: float, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return round(max(low, min(high, float(value))), 4)
