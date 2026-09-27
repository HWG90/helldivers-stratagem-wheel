"""Windows name fallback: Windows.Media.Ocr, then RapidOCR, then Tesseract."""

from PIL import Image, ImageDraw

import stratagems.name_ocr as name_ocr
from stratagems.name_ocr import NameOcrUnavailable, read_lines


def test_windows_uses_rapidocr_when_media_ocr_cannot_be_called(monkeypatch) -> None:
    monkeypatch.setattr(name_ocr.sys, "platform", "win32")

    def unavailable(_image: Image.Image) -> list[str]:
        raise NameOcrUnavailable("frozen app")

    def rapid(_image: Image.Image) -> list[str]:
        return ["RESUPPLY"]

    def tesseract(*_args: object, **_kwargs: object) -> list[str]:
        raise AssertionError("Tesseract ran on Windows")

    monkeypatch.setattr(name_ocr, "_windows_media_lines", unavailable)
    monkeypatch.setattr(name_ocr, "_rapidocr_lines", rapid)
    monkeypatch.setattr(name_ocr, "_tesseract_lines", tesseract)
    monkeypatch.setattr(name_ocr.pytesseract, "image_to_data", tesseract)
    assert read_lines(Image.new("RGB", (16, 16), "black")) == ["RESUPPLY"]


def test_windows_media_ocr_is_the_name_reader_when_it_runs(monkeypatch) -> None:
    monkeypatch.setattr(name_ocr.sys, "platform", "win32")

    def media(_image: Image.Image) -> list[str]:
        return ["EAGLE AIRSTRIKE"]

    def refused(*_args: object, **_kwargs: object) -> list[str]:
        raise AssertionError("fallback ran")

    monkeypatch.setattr(name_ocr, "_windows_media_lines", media)
    monkeypatch.setattr(name_ocr, "_rapidocr_lines", refused)
    monkeypatch.setattr(name_ocr, "_tesseract_lines", refused)
    assert read_lines(Image.new("RGB", (16, 16), "black")) == ["EAGLE AIRSTRIKE"]


def _writing() -> Image.Image:
    image = Image.new("RGB", (120, 48), "black")
    draw = ImageDraw.Draw(image)
    for x in range(8, 112, 5):
        draw.line((x, 8, x, 40), fill="white", width=2)
    return image


def test_windows_uses_tesseract_when_media_ocr_and_rapidocr_return_nothing(monkeypatch) -> None:
    monkeypatch.setattr(name_ocr.sys, "platform", "win32")
    calls: list[str] = []

    def empty(_image: Image.Image) -> list[str]:
        return []

    def tesseract(_image: Image.Image) -> list[str]:
        calls.append("tesseract")
        return ["RESUPPLY"]

    monkeypatch.setattr(name_ocr, "_windows_media_lines", empty)
    monkeypatch.setattr(name_ocr, "_rapidocr_lines", empty)
    monkeypatch.setattr(name_ocr, "_tesseract_lines", tesseract)
    assert read_lines(_writing()) == ["RESUPPLY"]
    assert calls == ["tesseract"]


def test_windows_skips_tesseract_when_the_crop_has_no_text(monkeypatch) -> None:
    monkeypatch.setattr(name_ocr.sys, "platform", "win32")

    def empty(_image: Image.Image) -> list[str]:
        return []

    def tesseract(_image: Image.Image) -> list[str]:
        raise AssertionError("Tesseract ran on a blank crop")

    monkeypatch.setattr(name_ocr, "_windows_media_lines", empty)
    monkeypatch.setattr(name_ocr, "_rapidocr_lines", empty)
    monkeypatch.setattr(name_ocr, "_tesseract_lines", tesseract)
    assert read_lines(Image.new("RGB", (32, 32), "black")) == []
