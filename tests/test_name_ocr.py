"""Windows name fallback uses Windows.Media.Ocr, then RapidOCR. Never Tesseract."""

from PIL import Image

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
