"""Synthetic arrow strips decode without Tesseract, then again from the LUT."""

import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from stratagems.catalog import get
from stratagems.glyphs import arrow_preview, geometry_direction, read_loadout
from stratagems.name_ocr import NameRead
from stratagems.ocr import scan_image


def _triangle(draw: ImageDraw.ImageDraw, direction: str, origin: tuple[int, int], size: int) -> None:
    x, y = origin
    if direction == "up":
        points = [(x + size // 2, y), (x + size - 1, y + size - 1), (x, y + size - 1)]
    elif direction == "down":
        points = [(x, y), (x + size - 1, y), (x + size // 2, y + size - 1)]
    elif direction == "left":
        points = [(x, y + size // 2), (x + size - 1, y), (x + size - 1, y + size - 1)]
    elif direction == "right":
        points = [(x, y), (x, y + size - 1), (x + size - 1, y + size // 2)]
    else:
        raise AssertionError(direction)
    draw.polygon(points, fill=(255, 255, 255))


def _strip(directions: list[str], *, icon: bool = False) -> Image.Image:
    size = 48
    gap = 18
    margin = 20
    icons = 70 if icon else 0
    width = margin + icons + len(directions) * (size + gap)
    image = Image.new("RGB", (width, size + margin * 2), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    if icon:
        draw.rectangle((16, margin, 16 + size, margin + size), fill=(255, 255, 255))
    x = margin + icons
    for direction in directions:
        _triangle(draw, direction, (x, margin), size)
        x += size + gap
    return image


def test_triangle_strip_decodes_without_tesseract_then_from_the_lut(monkeypatch) -> None:
    def refuse_ocr(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("name OCR ran")

    monkeypatch.setattr("stratagems.glyphs.read_names", refuse_ocr)
    monkeypatch.setattr("stratagems.ocr.pytesseract.image_to_data", refuse_ocr)
    monkeypatch.setattr("stratagems.name_ocr.pytesseract.image_to_data", refuse_ocr)

    code = ["up", "down", "right", "left", "up"]
    image = _strip(code)
    first = scan_image(image)
    assert [entry.name for entry in first.entries] == ["Reinforce"]
    assert list(first.entries[0].code) == code
    assert first.entries[0].code_source == "screen"
    assert first.reader == "arrows"
    for direction in ("up", "down", "left", "right"):
        assert first.glyph_lut[direction]

    monkeypatch.setattr(
        "stratagems.glyphs.geometry_direction",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("geometry ran on the second pass")),
    )
    second = scan_image(image, glyph_lut=first.glyph_lut, icon_lut=first.icon_lut)
    assert list(second.entries[0].code) == code
    assert second.entries[0].name == "Reinforce"

    preview, summary = arrow_preview(image, glyph_lut=first.glyph_lut)
    assert summary == "up down right left up"
    assert preview.getpixel((preview.width // 2, image.height + 8)) != (8, 8, 8)


def test_icon_lut_picks_the_stratagem_when_the_code_is_shared(monkeypatch) -> None:
    monkeypatch.setattr(
        "stratagems.glyphs.read_names",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("name OCR ran")),
    )
    pods = get("Reinforcement Pods")
    upload = get("Upload Data")
    assert pods is not None and upload is not None
    assert pods.code == upload.code
    image = _strip(list(pods.code), icon=True)
    learned = read_loadout(image, catalog=(pods,))
    assert learned.entries[0].name == "Reinforcement Pods"
    assert "Reinforcement Pods" in learned.icon_lut
    confirmed = read_loadout(
        image,
        glyph_lut=learned.glyph_lut,
        icon_lut=learned.icon_lut,
        catalog=(pods, upload),
    )
    assert confirmed.entries[0].name == "Reinforcement Pods"
    assert confirmed.entries[0].code == pods.code


def _chevron_bits(size: int = 48, thick: int = 16) -> bytearray:
    """A thick right-pointing chevron. This is not a filled triangle."""
    bits = bytearray(size * size)
    for y in range(size):
        span = abs(y - size // 2)
        tip = size - 4
        x = tip - int(span * 0.9)
        for offset in range(thick):
            column = x - offset
            if 0 <= column < size:
                bits[y * size + column] = 1
    return bits


def test_chevron_glyph_is_not_required_to_match_synthetic_triangles() -> None:
    bits = _chevron_bits()
    assert geometry_direction(bits, 48, 48) is None


def test_recognized_name_fills_the_loadout_when_arrow_classification_fails(monkeypatch) -> None:
    monkeypatch.setattr("stratagems.glyphs.geometry_direction", lambda *_args, **_kwargs: None)

    def names(_image: Image.Image) -> NameRead:
        return NameRead(["Resupply"], "rapidocr")

    monkeypatch.setattr("stratagems.glyphs.read_names", names)
    image = _strip(["up", "down", "right", "left", "up"])
    result = read_loadout(image)
    resupply = get("Resupply")
    assert resupply is not None
    assert result.reader == "rapidocr"
    assert result.entries[0].name == "Resupply"
    assert result.entries[0].code == resupply.code
    assert result.entries[0].code_source == "table"
    assert result.failure == ""


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")
def test_tesseract_reads_the_name_when_the_glyph_is_not_a_triangle() -> None:
    bits = _chevron_bits()
    assert geometry_direction(bits, 48, 48) is None
    image = Image.new("RGB", (640, 120), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    draw.text((24, 30), "RESUPPLY", fill=(255, 255, 255), font=font)
    for y in range(48):
        for x in range(48):
            if bits[y * 48 + x]:
                image.putpixel((520 + x, 36 + y), (255, 255, 255))
    result = read_loadout(image)
    resupply = get("Resupply")
    assert resupply is not None
    assert [entry.name for entry in result.entries] == ["Resupply"]
    assert result.entries[0].code == resupply.code
    assert result.reader == "tesseract"
