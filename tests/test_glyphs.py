"""Saved arrow samples decode a strip. A scan without samples does not guess."""

import threading

from PIL import Image, ImageDraw

from stratagems.app import App, _wheel_entries
from stratagems.catalog import get
from stratagems.config import Region
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


def _ring(size: int = 48) -> bytearray:
    bits = bytearray(size * size)
    for y in range(size):
        for x in range(size):
            if min(x, y, size - 1 - x, size - 1 - y) < 6:
                bits[y * size + x] = 1
    return bits


def _paint_row(image: Image.Image, glyphs: list[bytearray], *, top: int, size: int = 48) -> None:
    gap = 18
    x = 20
    for bits in glyphs:
        _paint(bits, size, (x, top), image)
        x += size + gap


def test_unmatched_shapes_are_skipped_and_matching_rows_import(monkeypatch) -> None:
    monkeypatch.setattr("stratagems.name_ocr.read_names", _refuse_ocr)
    monkeypatch.setattr("stratagems.ocr.pytesseract.image_to_data", _refuse_ocr)
    lut, glyphs = _chevron_lut()
    code = ["up", "down", "right", "left", "up"]
    ring = _ring()
    size = 48
    matched = [glyphs[direction] for direction in code]
    matched.insert(2, ring)
    height = 20 + size + 30 + size + 20
    width = 20 + 6 * (size + 18)
    image = Image.new("RGB", (width, height), (0, 0, 0))
    _paint_row(image, [ring, ring, ring, ring, ring], top=20)
    _paint_row(image, matched, top=20 + size + 30)
    result = read_loadout(image, glyph_lut=lut)
    assert [entry.name for entry in result.entries] == ["Reinforce"]
    assert list(result.entries[0].code) == code
    assert result.failure == ""
    assert result.note == "Some shapes were ignored."

    rings_only = Image.new("RGB", (width, size + 40), (0, 0, 0))
    _paint_row(rings_only, [ring, ring, ring, ring, ring], top=20)
    missed = read_loadout(rings_only, glyph_lut=lut)
    assert missed.entries == []
    assert "Row" not in missed.failure
    assert "does not match a saved sample" not in missed.failure
    assert "Some shapes were ignored." in missed.failure


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


_MISSION_ROWS = (
    ("up down right up", "SoS Beacon"),
    ("down down up right", "Resupply"),
    ("left down right down left down up left right", "TD-110 Maelstrom"),
    ("down left down up up right", "AC-8 Autocannon"),
    ("up right down down down", "Eagle 500kg Bomb"),
    ("right right down left right down", "Orbital 120mm HE Barrage"),
    ("right down left up up", "Orbital Gatling Barrage"),
)


def _stack(rows: list[list[str]], glyphs: dict[str, bytearray], *, size: int = 48) -> Image.Image:
    gap = 18
    row_gap = 28
    margin = 20
    width = margin * 2 + max(len(row) for row in rows) * (size + gap)
    height = margin * 2 + len(rows) * size + (len(rows) - 1) * row_gap
    image = Image.new("RGB", (width, height), (0, 0, 0))
    for index, row in enumerate(rows):
        top = margin + index * (size + row_gap)
        _paint_row(image, [glyphs[direction] for direction in row], top=top, size=size)
    return image


class _InlineThread:
    def __init__(self, target: object = None, args: tuple[object, ...] = (), kwargs: dict[str, object] | None = None, daemon: bool | None = None) -> None:
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self) -> None:
        target = self._target
        if callable(target):
            target(*self._args, **self._kwargs)


def test_seven_decoded_rows_all_import(monkeypatch) -> None:
    monkeypatch.setattr("stratagems.name_ocr.read_names", _refuse_ocr)
    monkeypatch.setattr("stratagems.ocr.pytesseract.image_to_data", _refuse_ocr)
    lut, glyphs = _chevron_lut()
    rows = [code.split() for code, _name in _MISSION_ROWS]
    image = _stack(rows, glyphs)
    result = read_loadout(image, glyph_lut=lut)
    assert [entry.name for entry in result.entries] == [name for _code, name in _MISSION_ROWS]
    assert len(result.entries) == 7
    assert result.failure == ""
    assert result.reader == "samples"
    _preview, summary = arrow_preview(image, glyph_lut=lut)
    for code, _name in _MISSION_ROWS:
        assert code in summary.splitlines()


def test_three_codes_in_one_capture_all_land_on_the_wheel(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(threading, "Thread", _InlineThread)
    monkeypatch.setattr("stratagems.name_ocr.read_names", _refuse_ocr)
    monkeypatch.setattr("stratagems.ocr.pytesseract.image_to_data", _refuse_ocr)
    lut, glyphs = _chevron_lut()
    codes = [
        ["up", "right", "down", "down", "down"],
        ["up", "up", "up", "up"],
        ["down", "left", "down", "up", "up", "right"],
        ["right", "down", "left", "up", "up"],
    ]
    image = _stack(codes, glyphs)

    def capture(*_args: object, **_kwargs: object) -> Image.Image:
        return image

    monkeypatch.setattr("stratagems.app.capture_region", capture)
    app = App(demo=True)
    app.config.ocr_fallback = True
    try:
        app.config.region = Region(0, 0, image.width, image.height)
        app.config.glyph_lut = lut
        app.scan()
        app.root.update()
        app.present(0, 0, dry_run=True)
        names = [entry.name for entry in app.overlay.entries]
        assert names == [
            "Reinforce",
            "Resupply",
            "Eagle 500kg Bomb",
            "AC-8 Autocannon",
            "Orbital Gatling Barrage",
        ]
        assert "up up up up" not in names
        wheel = _wheel_entries(app._cache or [])
        assert [entry.name for entry in wheel] == names
    finally:
        app.root.destroy()


def test_padded_and_failed_rows_keep_the_other_matches(monkeypatch) -> None:
    monkeypatch.setattr("stratagems.name_ocr.read_names", _refuse_ocr)
    monkeypatch.setattr("stratagems.ocr.pytesseract.image_to_data", _refuse_ocr)
    lut, glyphs = _chevron_lut()
    maelstrom = "left down right down left down up left right".split()
    rows = [
        ["left", "down", "down", "up", "right", "left"],
        ["up", "up", "up", "up"],
        ["left", "left", "left", "left", *maelstrom, "left", "left", "left", "left"],
    ]
    assert len(rows[2]) > 12
    result = read_loadout(_stack(rows, glyphs), glyph_lut=lut)
    assert [entry.name for entry in result.entries] == ["Resupply", "TD-110 Maelstrom"]
    assert result.failure == ""


def _sample_triangle(direction: str) -> str:
    clusters = cluster_glyphs(_strip([direction]))
    assert len(clusters) == 1
    return lut_from_tags(clusters, [direction])[direction][0]
