"""Synthetic arrow strips decode without Tesseract, then again from the LUT."""

from PIL import Image, ImageDraw

from stratagems.catalog import get
from stratagems.glyphs import arrow_preview, read_loadout
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

    monkeypatch.setattr("stratagems.glyphs.read_lines", refuse_ocr)
    monkeypatch.setattr("stratagems.ocr.pytesseract.image_to_data", refuse_ocr)
    monkeypatch.setattr("stratagems.name_ocr.pytesseract.image_to_data", refuse_ocr)

    code = ["up", "down", "right", "left", "up"]
    image = _strip(code)
    first = scan_image(image)
    assert [entry.name for entry in first.entries] == ["Reinforce"]
    assert list(first.entries[0].code) == code
    assert first.entries[0].code_source == "screen"
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
        "stratagems.glyphs.read_lines",
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
