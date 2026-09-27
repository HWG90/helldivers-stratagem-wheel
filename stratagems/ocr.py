"""Capture a screen region and read stratagem rows from it."""

from __future__ import annotations

from pathlib import Path

import mss
import pytesseract
from PIL import Image, ImageGrab, ImageOps, ImageStat
from pytesseract import TesseractError, TesseractNotFoundError

from stratagems.catalog import LoadoutEntry
from stratagems.matching import resolve_lines


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


def scan_image(image: Image.Image) -> list[LoadoutEntry]:
    return resolve_lines(lines_from_image(image))


def lines_from_image(image: Image.Image) -> list[str]:
    prepared = preprocess(image)
    try:
        data = pytesseract.image_to_data(
            prepared,
            output_type=pytesseract.Output.DICT,
            config="--psm 6 -l eng",
        )
    except TesseractNotFoundError as exc:
        raise OcrError(
            "Tesseract is not installed or not on PATH. Install tesseract-ocr and try the scan again."
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
