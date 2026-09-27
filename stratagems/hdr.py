"""Tone curve for HDR screenshots before OCR.

Windows HDR often returns a flat, dark, or clipped crop through ordinary
screen capture. This module remaps that crop with exposure, black level,
gamma, and contrast. It does not read another process.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from stratagems.config import Config

EXPOSURE_MIN = -4.0
EXPOSURE_MAX = 4.0
GAMMA_MIN = 0.20
GAMMA_MAX = 3.0
CONTRAST_MIN = 0.25
CONTRAST_MAX = 3.0
BLACK_MIN = 0.0
BLACK_MAX = 0.95

EXPOSURE_STEP = 0.05
GAMMA_STEP = 0.05
CONTRAST_STEP = 0.05
BLACK_STEP = 0.01

# Where Auto tries to place the bright tail after the black point.
_TEXT_TARGET = 0.90


@dataclass(frozen=True)
class HdrCurve:
    exposure_stops: float = 0.0
    gamma: float = 1.0
    contrast: float = 1.0
    black_level: float = 0.0

    def clamped(self) -> HdrCurve:
        return HdrCurve(
            exposure_stops=_clamp(self.exposure_stops, EXPOSURE_MIN, EXPOSURE_MAX),
            gamma=_clamp(self.gamma, GAMMA_MIN, GAMMA_MAX),
            contrast=_clamp(self.contrast, CONTRAST_MIN, CONTRAST_MAX),
            black_level=_clamp(self.black_level, BLACK_MIN, BLACK_MAX),
        )


def curve_from_config(config: Config) -> HdrCurve:
    return HdrCurve(
        exposure_stops=config.hdr_exposure,
        gamma=config.hdr_gamma,
        contrast=config.hdr_contrast,
        black_level=config.hdr_black_level,
    )


def prepare_scan_image(image: Image.Image, *, enabled: bool, curve: HdrCurve) -> Image.Image:
    """Return the capture OCR should see. Disabled leaves the image untouched."""
    if not enabled:
        return image
    return apply_hdr(image, curve)


def apply_hdr(image: Image.Image, curve: HdrCurve) -> Image.Image:
    """Apply the curve to every RGB channel.

    Order is exposure (stops), black level, gamma, then contrast about mid gray.
    Gamma below 1 lifts midtones. An identity curve returns the RGB image as-is.
    """
    curve = curve.clamped()
    rgb = image.convert("RGB")
    if _is_identity(curve):
        return rgb
    # Pillow wants one 256-entry table per band.
    return rgb.point(_lut(curve) * len(rgb.getbands()))


def auto_curve(image: Image.Image) -> HdrCurve:
    """Pick a curve from the crop histogram.

    Light text on a dark panel is the case this is aimed at: the black point
    sits on the dark mass and exposure lifts the bright tail. A blown-out crop
    gets the same treatment, which pulls the compressed highlights apart.
    Percentiles ignore a lone clipped pixel that would pin autocontrast.
    """
    gray = image.convert("L")
    hist = gray.histogram()
    total = sum(hist)
    if total <= 0:
        return HdrCurve()

    shadow = _percentile(hist, total, 0.05)
    highlight = _percentile(hist, total, 0.99)
    separation = highlight - shadow
    denom = separation + _TEXT_TARGET * shadow
    if denom < 1e-6:
        return HdrCurve()

    gain = _TEXT_TARGET / denom
    gain = min(2.0 ** EXPOSURE_MAX, max(2.0 ** EXPOSURE_MIN, gain))
    exposure = _snap(math.log2(gain), EXPOSURE_STEP)
    applied = 2.0 ** exposure
    black = _snap(min(BLACK_MAX, max(0.0, shadow * applied)), BLACK_STEP)
    return HdrCurve(
        exposure_stops=exposure,
        gamma=1.0,
        contrast=_snap(1.2, CONTRAST_STEP),
        black_level=black,
    ).clamped()


def _lut(curve: HdrCurve) -> list[int]:
    gain = 2.0 ** curve.exposure_stops
    black = curve.black_level
    span = max(1e-6, 1.0 - black)
    gamma = curve.gamma
    contrast = curve.contrast
    use_gamma = abs(gamma - 1.0) > 1e-6
    table: list[int] = []
    for level in range(256):
        value = (level / 255.0) * gain
        value = (value - black) / span
        value = _clamp(value, 0.0, 1.0)
        if use_gamma:
            value = value ** gamma
        value = (value - 0.5) * contrast + 0.5
        table.append(int(round(_clamp(value, 0.0, 1.0) * 255.0)))
    return table


def _percentile(hist: list[int], total: int, fraction: float) -> float:
    target = total * fraction
    seen = 0
    for level, count in enumerate(hist):
        seen += count
        if seen >= target:
            return level / 255.0
    return 1.0


def _is_identity(curve: HdrCurve) -> bool:
    return (
        abs(curve.exposure_stops) < 1e-6
        and abs(curve.gamma - 1.0) < 1e-6
        and abs(curve.contrast - 1.0) < 1e-6
        and curve.black_level <= 1e-6
    )


def _snap(value: float, step: float) -> float:
    if step <= 0:
        return value
    return round(round(value / step) * step, 4)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
