"""Saved arrow samples decode a strip. A scan without samples does not guess."""

from PIL import Image, ImageDraw

from stratagems.catalog import get
from stratagems.glyphs import (
    arrow_preview,
    cluster_glyphs,
    geometry_direction,
    lut_from_tags,
    read_loadout,
)
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


def _rotate_ccw(bits: bytearray, size: int) -> bytearray:
    out = bytearray(size * size)
    for y in range(size):
        for x in range(size):
            if bits[y * size + x]:
                out[(size - 1 - x) * size + y] = 1
    return out


def _rotate_cw(bits: bytearray, size: int) -> bytearray:
    out = bytearray(size * size)
    for y in range(size):
        for x in range(size):
            if bits[y * size + x]:
                out[x * size + (size - 1 - y)] = 1
    return out


def _mirror(bits: bytearray, size: int) -> bytearray:
    out = bytearray(size * size)
    for y in range(size):
        for x in range(size):
            if bits[y * size + x]:
                out[y * size + (size - 1 - x)] = 1
    return out


def _paint(bits: bytearray, size: int, origin: tuple[int, int], image: Image.Image) -> None:
    ox, oy = origin
    for y in range(size):
        row = y * size
        for x in range(size):
            if bits[row + x]:
                image.putpixel((ox + x, oy + y), (255, 255, 255))


def _glyph_image(bits: bytearray, size: int = 48) -> Image.Image:
    margin = 20
    image = Image.new("RGB", (size + margin * 2, size + margin * 2), (0, 0, 0))
    _paint(bits, size, (margin, margin), image)
    return image


def _sample(bits: bytearray, direction: str) -> str:
    clusters = cluster_glyphs(_glyph_image(bits))
    assert len(clusters) == 1
    tagged = lut_from_tags(clusters, [direction])
    return tagged[direction][0]


def _chevron_lut() -> tuple[dict[str, list[str]], dict[str, bytearray]]:
    size = 48
    right_thick = _chevron_bits(size, 16)
    right_thicker = _chevron_bits(size, 22)
    drawn = {
        "right": (right_thick, right_thicker),
        "left": (_mirror(right_thick, size), _mirror(right_thicker, size)),
        "up": (_rotate_ccw(right_thick, size), _rotate_ccw(right_thicker, size)),
        "down": (_rotate_cw(right_thick, size), _rotate_cw(right_thicker, size)),
    }
    lut: dict[str, list[str]] = {}
    first: dict[str, bytearray] = {}
    for direction, (thin, thick) in drawn.items():
        assert geometry_direction(thin, size, size) is None
        assert geometry_direction(thick, size, size) is None
        first_patch = _sample(thin, direction)
        second_patch = _sample(thick, direction)
        assert first_patch != second_patch
        lut[direction] = [first_patch, second_patch]
        first[direction] = thin
    return lut, first


def _chevron_strip(directions: list[str], glyphs: dict[str, bytearray], *, size: int = 48) -> Image.Image:
    gap = 18
    margin = 20
    width = margin + len(directions) * (size + gap)
    image = Image.new("RGB", (width, size + margin * 2), (0, 0, 0))
    x = margin
    for direction in directions:
        _paint(glyphs[direction], size, (x, margin), image)
        x += size + gap
    return image


def _refuse_ocr(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("OCR ran")


def _refuse_geometry(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("geometry ran")


def test_saved_chevrons_decode_a_catalog_stratagem_without_ocr(monkeypatch) -> None:
    monkeypatch.setattr("stratagems.glyphs.geometry_direction", _refuse_geometry)
    monkeypatch.setattr("stratagems.name_ocr.read_names", _refuse_ocr)
    monkeypatch.setattr("stratagems.ocr.pytesseract.image_to_data", _refuse_ocr)
    lut, glyphs = _chevron_lut()
    code = ["up", "down", "right", "left", "up"]
    image = _chevron_strip(code, glyphs)
    result = scan_image(image, glyph_lut=lut)
    reinforce = get("Reinforce")
    assert reinforce is not None
    assert [entry.name for entry in result.entries] == ["Reinforce"]
    assert list(result.entries[0].code) == list(reinforce.code)
    assert result.entries[0].code_source == "screen"
    assert result.reader == "samples"
    for direction in ("up", "down", "left", "right"):
        assert len(lut[direction]) == 2

    preview, summary = arrow_preview(image, glyph_lut=lut)
    assert summary == "up down right left up"
    assert preview.getpixel((preview.width // 2, image.height + 8)) != (8, 8, 8)


def test_scan_without_samples_tells_the_user_to_learn(monkeypatch) -> None:
    monkeypatch.setattr("stratagems.glyphs.geometry_direction", _refuse_geometry)
    monkeypatch.setattr("stratagems.name_ocr.read_names", _refuse_ocr)
    monkeypatch.setattr("stratagems.ocr.pytesseract.image_to_data", _refuse_ocr)
    result = read_loadout(_strip(["up", "down", "right", "left", "up"]))
    assert result.entries == []
    assert "Learn" in result.failure


def test_an_unmatched_glyph_names_the_row_and_returns_nothing(monkeypatch) -> None:
    monkeypatch.setattr("stratagems.name_ocr.read_names", _refuse_ocr)
    lut, _glyphs = _chevron_lut()
    size = 48
    ring = bytearray(size * size)
    for y in range(size):
        for x in range(size):
            if min(x, y, size - 1 - x, size - 1 - y) < 6:
                ring[y * size + x] = 1
    gap = 18
    margin = 20
    width = margin + 5 * (size + gap)
    image = Image.new("RGB", (width, size + margin * 2), (0, 0, 0))
    x = margin
    for _index in range(5):
        _paint(ring, size, (x, margin), image)
        x += size + gap
    result = read_loadout(image, glyph_lut=lut)
    assert result.entries == []
    assert result.failure == "Row 1 has an arrow that does not match a saved sample."


def test_icon_lut_picks_the_stratagem_when_the_code_is_shared(monkeypatch) -> None:
    monkeypatch.setattr("stratagems.name_ocr.read_names", _refuse_ocr)
    monkeypatch.setattr("stratagems.ocr.pytesseract.image_to_data", _refuse_ocr)
    lut = {
        direction: [_sample_triangle(direction)]
        for direction in ("up", "down", "left", "right")
    }
    pods = get("Reinforcement Pods")
    upload = get("Upload Data")
    assert pods is not None and upload is not None
    assert pods.code == upload.code
    image = _strip(list(pods.code), icon=True)
    learned = read_loadout(image, glyph_lut=lut, catalog=(pods,))
    assert learned.entries[0].name == "Reinforcement Pods"
    assert "Reinforcement Pods" in learned.icon_lut
    confirmed = read_loadout(
        image,
        glyph_lut=lut,
        icon_lut=learned.icon_lut,
        catalog=(pods, upload),
    )
    assert confirmed.entries[0].name == "Reinforcement Pods"
    assert confirmed.entries[0].code == pods.code


def _sample_triangle(direction: str) -> str:
    clusters = cluster_glyphs(_strip([direction]))
    assert len(clusters) == 1
    return lut_from_tags(clusters, [direction])[direction][0]
