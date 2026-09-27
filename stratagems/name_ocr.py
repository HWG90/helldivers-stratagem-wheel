"""Name fallback. Arrow codes are not read here.

On Windows the packaged app calls Windows.Media.Ocr. If that API cannot be
called, RapidOCR (ONNX Runtime) reads the name. Tesseract is not used on
Windows. EasyOCR and PaddleOCR are not used.
"""

from __future__ import annotations

import asyncio
import io
import sys

import pytesseract
from PIL import Image, ImageOps, ImageStat
from pytesseract import TesseractError, TesseractNotFoundError

from stratagems.runtime import configure_bundled_runtime, tesseract_config

try:
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream
except ImportError:
    Language = None
    BitmapDecoder = None
    OcrEngine = None
    DataWriter = None
    InMemoryRandomAccessStream = None

try:
    from rapidocr import RapidOCR
except ImportError:
    RapidOCR = None  # type: ignore[misc, assignment]


class NameOcrUnavailable(Exception):
    """Windows.Media.Ocr cannot be called in this process."""


_rapid_engine: object | None = None


def read_lines(image: Image.Image) -> list[str]:
    """Read text lines. On Windows this never calls Tesseract."""
    if sys.platform == "win32":
        try:
            return _windows_media_lines(image)
        except NameOcrUnavailable:
            return _rapidocr_lines(image)
    return _tesseract_lines(image)


def _windows_media_lines(image: Image.Image) -> list[str]:
    if (
        OcrEngine is None
        or BitmapDecoder is None
        or DataWriter is None
        or InMemoryRandomAccessStream is None
    ):
        raise NameOcrUnavailable("Windows.Media.Ocr projections are not installed")
    payload = io.BytesIO()
    image.convert("RGB").save(payload, format="PNG")
    data = payload.getvalue()
    try:
        return asyncio.run(_recognize(data))
    except NameOcrUnavailable:
        raise
    except Exception as exc:
        raise NameOcrUnavailable(str(exc)) from exc


async def _recognize(data: bytes) -> list[str]:
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(data)
    await writer.store_async()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None and Language is not None:
        english = Language("en-US")
        if OcrEngine.is_language_supported(english):
            engine = OcrEngine.try_create_from_language(english)
    if engine is None:
        raise NameOcrUnavailable("Windows.Media.Ocr has no language pack")
    result = await engine.recognize_async(bitmap)
    lines: list[str] = []
    for line in getattr(result, "lines", []) or []:
        text = str(getattr(line, "text", "") or "").strip()
        if text:
            lines.append(text)
    if lines:
        return lines
    text = str(getattr(result, "text", "") or "").strip()
    return [text] if text else []


def _rapidocr_lines(image: Image.Image) -> list[str]:
    global _rapid_engine
    if RapidOCR is None:
        return []
    try:
        if _rapid_engine is None:
            _rapid_engine = RapidOCR()
        payload = io.BytesIO()
        image.convert("RGB").save(payload, format="PNG")
        result = _rapid_engine(payload.getvalue())
    except Exception:
        return []
    texts = getattr(result, "txts", None)
    if texts:
        return [str(item).strip() for item in texts if str(item).strip()]
    rows = result[0] if isinstance(result, tuple) and result else None
    if not isinstance(rows, list):
        return []
    lines: list[str] = []
    for item in rows:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            text = str(item[1]).strip()
            if text:
                lines.append(text)
    return lines


def _tesseract_lines(image: Image.Image) -> list[str]:
    configure_bundled_runtime()
    gray = ImageOps.autocontrast(image.convert("L"))
    if ImageStat.Stat(gray).mean[0] < 128:
        gray = ImageOps.invert(gray)
    try:
        data = pytesseract.image_to_data(
            gray,
            output_type=pytesseract.Output.DICT,
            config=tesseract_config(),
        )
    except (TesseractNotFoundError, TesseractError):
        return []
    grouped: dict[tuple[int, int, int], list[str]] = {}
    texts = data.get("text", [])
    for index, raw in enumerate(texts):
        word = str(raw).strip()
        if not word:
            continue
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError, KeyError, IndexError):
            confidence = -1.0
        if confidence < 0:
            continue
        key = (
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )
        grouped.setdefault(key, []).append(word)
    return [" ".join(words) for words in grouped.values()]
