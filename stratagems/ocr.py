"""Capture a screen region and read stratagem rows from it."""

from __future__ import annotations

from pathlib import Path

import mss
import pytesseract
from PIL import Image, ImageGrab, ImageOps, ImageStat
from pytesseract import TesseractError, TesseractNotFoundError

from stratagems.glyphs import ScanResult, read_loadout
from stratagems.hdr import HdrCurve, prepare_scan_image
from stratagems.runtime import configure_bundled_runtime, tesseract_config


class OcrError(Exception):
    """The local OCR engine could not read the capture."""


def capture_region(left: int, top: int, width: int, height: int) -> Image.Image:
    if width < 1 or height < 1:
        raise OcrError("The capture region is empty.")
    try:
        return _capture_mss(left, top, width, height)
    except Exception as mss_error:
        # Some Linux X visuals reject mss. Pillow's grabber is the same
        # user-space screenshot, still not a game hook.
        try:
            return _capture_pillow(left, top, width, height)
        except Exception as pillow_error:
            raise OcrError(f"Could not capture the screen ({mss_error}; {pillow_error})") from pillow_error


def _capture_mss(left: int, top: int, width: int, height: int) -> Image.Image:
    with mss.mss() as sct:
        raw = sct.grab({"left": left, "top": top, "width": width, "height": height})
    return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def _capture_pillow(left: int, top: int, width: int, height: int) -> Image.Image:
    grabbed = ImageGrab.grab(bbox=(left, top, left + width, top + height), all_screens=True)
    if grabbed.size != (width, height):
        grabbed = grabbed.resize((width, height))
    return grabbed.convert("RGB")


def save_bbox(left: int, top: int, width: int, height: int, path: Path) -> None:
    capture_region(left, top, width, height).save(path)


def virtual_screen() -> tuple[Image.Image, int, int]:
    """Return the full desktop image and its origin in screen coordinates."""
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            raw = sct.grab(monitor)
            image = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        return image, int(monitor["left"]), int(monitor["top"])
    except Exception:
        image = ImageGrab.grab(all_screens=True).convert("RGB")
        return image, 0, 0


def scan_image(
    image: Image.Image,
    *,
    hdr: bool = False,
    curve: HdrCurve | None = None,
    glyph_lut: dict[str, list[str]] | None = None,
    icon_lut: dict[str, str] | None = None,
) -> ScanResult:
    """Read a mission loadout. Arrow shapes supply the code. OCR is names only."""
    return read_loadout(
        image,
        hdr=hdr,
        curve=curve,
        glyph_lut=glyph_lut,
        icon_lut=icon_lut,
    )


def ocr_bitmap(
    image: Image.Image,
    *,
    hdr: bool = False,
    curve: HdrCurve | None = None,
) -> Image.Image:
    """Return the bitmap ``image_to_data`` receives.

    The crop is passed through the HDR curve only when ``hdr`` is on, then
    through the same preprocessing as the OCR call. The preview shows this
    image, and ``lines_from_image`` hands the same object to Tesseract.
    """
    stage = prepare_scan_image(image, enabled=hdr, curve=curve or HdrCurve())
    return preprocess(stage)


def lines_from_image(
    image: Image.Image,
    *,
    hdr: bool = False,
    curve: HdrCurve | None = None,
) -> list[str]:
    configure_bundled_runtime()
    prepared = ocr_bitmap(image, hdr=hdr, curve=curve)
    try:
        data = pytesseract.image_to_data(
            prepared,
            output_type=pytesseract.Output.DICT,
            config=tesseract_config(),
        )
    except TesseractNotFoundError as exc:
        raise OcrError(
            "Tesseract was not found. The Windows app looks for tesseract\\tesseract.exe "
            "next to its runtime. A source checkout needs tesseract-ocr on PATH."
        ) from exc
    except TesseractError as exc:
        raise OcrError(f"Tesseract failed: {exc}") from exc

    grouped: dict[tuple[int, int, int], list[str]] = {}
    texts = data.get("text", [])
    for index, raw in enumerate(texts):
        word = str(raw).strip()
        if not word:
            continue
        conf = _confidence(data["conf"][index])
        if conf < 0:
            continue
        key = (
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )
        grouped.setdefault(key, []).append(word)
    return [" ".join(words) for words in grouped.values()]


def preprocess(image: Image.Image) -> Image.Image:
    gray = ImageOps.autocontrast(image.convert("L"))
    long_edge = max(gray.width, gray.height)
    scale = 2
    if long_edge * scale > 2000 and long_edge > 0:
        scale = max(1, 2000 // long_edge)
    if scale > 1:
        gray = gray.resize((gray.width * scale, gray.height * scale), Image.Resampling.LANCZOS)
    if ImageStat.Stat(gray).mean[0] < 128:
        gray = ImageOps.invert(gray)
    return gray


def _confidence(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0
