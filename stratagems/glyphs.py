"""Read stratagem arrow codes from samples the user tagged.

Learn segments the calibrated region and clusters identical glyphs. The user
tags each cluster Up, Down, Left, or Right. A scan compares every glyph to
those saved patches. It does not guess from triangle geometry, and it does
not call an OCR engine.
"""

from __future__ import annotations

import base64
import math
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

from stratagems.arrows import MAX_ARROWS, MIN_ARROWS
from stratagems.catalog import BY_NAME, STRATAGEMS, LoadoutEntry, Stratagem
from stratagems.hdr import HdrCurve, prepare_scan_image

PATCH = 24
PATCH_BYTES = PATCH * PATCH
MAX_SAMPLES = 6
MIN_NCC = 0.62
CLUSTER_NCC = 0.90
ICON_MIN = 0.58
_DIRECTIONS = ("up", "down", "left", "right")
_LEARN_HINT = "No arrow samples saved. Open the stratagem list and run Learn."


@dataclass
class ScanResult:
    entries: list[LoadoutEntry]
    glyph_lut: dict[str, list[str]]
    icon_lut: dict[str, str]
    reader: str = ""
    failure: str = ""


@dataclass
class _Hit:
    x: int
    y: int
    width: int
    height: int
    direction: str
    patch: bytes


@dataclass
class _Row:
    code: tuple[str, ...]
    hits: list[_Hit]
    icon: bytes | None
    name_box: tuple[int, int, int, int] | None


@dataclass
class GlyphCluster:
    """One unique arrow shape from a Learn capture."""

    patch: bytes
    count: int


@dataclass
class ShapeMemory:
    glyphs: dict[str, list[bytes]] = field(default_factory=dict)
    icons: dict[str, bytes] = field(default_factory=dict)

    def has_glyphs(self) -> bool:
        return any(self.glyphs.values())

    def nearest(self, patch: bytes) -> tuple[str, float]:
        best_direction = "up"
        best_score = -1.0
        for direction, samples in self.glyphs.items():
            for sample in samples:
                score = _ncc(patch, sample)
                if score > best_score:
                    best_score = score
                    best_direction = direction
        return best_direction, best_score

    def remember_glyph(self, direction: str, patch: bytes) -> None:
        samples = self.glyphs.setdefault(direction, [])
        for sample in samples:
            if _ncc(patch, sample) >= 0.97:
                return
        if len(samples) >= MAX_SAMPLES:
            return
        samples.append(patch)

    def match_icon(self, patch: bytes, candidates: list[Stratagem]) -> Stratagem | None:
        scored: list[tuple[float, Stratagem]] = []
        for item in candidates:
            sample = self.icons.get(item.name)
            if sample is None:
                continue
            scored.append((_ncc(patch, sample), item))
        if not scored:
            return None
        scored.sort(key=lambda item: item[0], reverse=True)
        if scored[0][0] < ICON_MIN:
            return None
        if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.08:
            return None
        return scored[0][1]

    def remember_icon(self, name: str, patch: bytes) -> None:
        if name not in BY_NAME:
            return
        self.icons[name] = patch

    def export(self) -> tuple[dict[str, list[str]], dict[str, str]]:
        glyphs = {
            direction: [_encode_patch(sample) for sample in samples]
            for direction, samples in self.glyphs.items()
            if samples
        }
        icons = {name: _encode_patch(sample) for name, sample in self.icons.items()}
        return glyphs, icons


def sanitize_glyph_lut(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    cleaned: dict[str, list[str]] = {}
    for key, samples in value.items():
        if key not in _DIRECTIONS or not isinstance(samples, list):
            continue
        kept: list[str] = []
        for sample in samples:
            if isinstance(sample, str) and _decode_patch(sample) is not None:
                kept.append(sample)
            if len(kept) >= MAX_SAMPLES:
                break
        if kept:
            cleaned[str(key)] = kept
    return cleaned


def sanitize_icon_lut(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    cleaned: dict[str, str] = {}
    for key, sample in value.items():
        if not isinstance(key, str) or key not in BY_NAME or not isinstance(sample, str):
            continue
        if _decode_patch(sample) is None:
            continue
        cleaned[key] = sample
    return cleaned


def memory_from_luts(glyph_lut: dict[str, list[str]] | None, icon_lut: dict[str, str] | None) -> ShapeMemory:
    memory = ShapeMemory()
    for direction, samples in sanitize_glyph_lut(glyph_lut or {}).items():
        decoded = [_decode_patch(sample) for sample in samples]
        memory.glyphs[direction] = [sample for sample in decoded if sample is not None]
    for name, sample in sanitize_icon_lut(icon_lut or {}).items():
        decoded = _decode_patch(sample)
        if decoded is not None:
            memory.icons[name] = decoded
    return memory


def cluster_glyphs(
    image: Image.Image,
    *,
    hdr: bool = False,
    curve: HdrCurve | None = None,
) -> list[GlyphCluster]:
    """Segment arrow glyphs and collapse identical shapes into one patch each."""
    prepared = _prepared(image, hdr=hdr, curve=curve)
    clusters: list[GlyphCluster] = []
    for patch in _arrow_patches(prepared):
        _add_cluster(clusters, patch)
    return clusters


def lut_from_tags(clusters: list[GlyphCluster], tags: list[str]) -> dict[str, list[str]]:
    """Build the config table from the direction the user gave each cluster."""
    lut: dict[str, list[str]] = {}
    for cluster, tag in zip(clusters, tags, strict=False):
        if tag not in _DIRECTIONS:
            continue
        samples = lut.setdefault(tag, [])
        encoded = _encode_patch(cluster.patch)
        if encoded in samples or len(samples) >= MAX_SAMPLES:
            continue
        samples.append(encoded)
    return lut


def read_loadout(
    image: Image.Image,
    *,
    hdr: bool = False,
    curve: HdrCurve | None = None,
    glyph_lut: dict[str, list[str]] | None = None,
    icon_lut: dict[str, str] | None = None,
    catalog: tuple[Stratagem, ...] | list[Stratagem] | None = None,
) -> ScanResult:
    """Map saved arrow samples onto the catalog. This does not call OCR."""
    prepared = _prepared(image, hdr=hdr, curve=curve)
    memory = memory_from_luts(glyph_lut, icon_lut)
    exported_glyphs, exported_icons = memory.export()
    if not memory.has_glyphs():
        return ScanResult([], exported_glyphs, exported_icons, failure=_LEARN_HINT)
    pool = tuple(catalog) if catalog is not None else STRATAGEMS
    entries: list[LoadoutEntry] = []
    seen: set[str] = set()
    for row_index, (run, icon) in enumerate(_runs(prepared), start=1):
        directions: list[str] = []
        for box in run:
            direction, score = memory.nearest(box.patch)
            if score < MIN_NCC:
                return ScanResult(
                    [],
                    exported_glyphs,
                    exported_icons,
                    failure=f"Row {row_index} has an arrow that does not match a saved sample.",
                )
            directions.append(direction)
        code = tuple(directions)
        chosen = _catalog_match(code, icon, memory, pool)
        if chosen is None:
            return ScanResult(
                [],
                exported_glyphs,
                exported_icons,
                failure=f"Row {row_index} did not match a stratagem.",
            )
        if icon is not None:
            memory.remember_icon(chosen.name, icon)
        key = chosen.name.casefold()
        if key in seen:
            continue
        seen.add(key)
        entries.append(LoadoutEntry(chosen.name, code, "screen"))
    exported_glyphs, exported_icons = memory.export()
    if not entries:
        return ScanResult([], exported_glyphs, exported_icons, failure="No arrow glyphs in the calibrated region.")
    return ScanResult(entries, exported_glyphs, exported_icons, reader="samples")


def arrow_preview(
    image: Image.Image,
    *,
    hdr: bool = False,
    curve: HdrCurve | None = None,
    glyph_lut: dict[str, list[str]] | None = None,
) -> tuple[Image.Image, str]:
    """Draw the segmented glyphs and the direction chosen for each.

    This does not write the look-up table and does not change a saved loadout.
    """
    prepared = _prepared(image, hdr=hdr, curve=curve)
    memory = memory_from_luts(glyph_lut, {})
    rows, _low_confidence = _segment(prepared, memory)
    return _draw_preview(prepared, rows), _preview_text(rows)


def geometry_direction(bits: bytearray, width: int, height: int) -> str | None:
    """Point a triangle by which side is the wide base."""
    if width < 6 or height < 6:
        return None
    row_width = [0] * height
    col_height = [0] * width
    for y in range(height):
        row = y * width
        for x in range(width):
            if bits[row + x]:
                row_width[y] += 1
                col_height[x] += 1
    top = _edge_mean(row_width, start=True)
    bottom = _edge_mean(row_width, start=False)
    left = _edge_mean(col_height, start=True)
    right = _edge_mean(col_height, start=False)
    scores = {
        "up": (bottom - top) / width,
        "down": (top - bottom) / width,
        "left": (right - left) / height,
        "right": (left - right) / height,
    }
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best, best_score = ordered[0]
    second = ordered[1][1]
    # A triangle has a wide base, a thin point, and almost no mass on the other axis.
    if best_score < 0.40 or second > 0.08:
        return None
    if best in ("up", "down"):
        peak = max(row_width)
        if peak <= 0 or min(row_width) / peak > 0.15:
            return None
    else:
        peak = max(col_height)
        if peak <= 0 or min(col_height) / peak > 0.15:
            return None
    return best


def _prepared(image: Image.Image, *, hdr: bool, curve: HdrCurve | None) -> Image.Image:
    stage = prepare_scan_image(image, enabled=hdr, curve=curve or HdrCurve())
    if stage is image:
        return image.copy()
    return stage


def _segment(prepared: Image.Image, memory: ShapeMemory) -> tuple[list[_Row], bool]:
    gray = prepared.convert("L")
    width, height = gray.size
    rows: list[_Row] = []
    low_confidence = False
    for top, bottom in _bands(_mask(gray)[0], width, height):
        band = gray.crop((0, top, width, bottom))
        mask, ink_is_light = _mask(band)
        comps = _components(mask, band.width, band.height)
        hits: list[_Hit] = []
        rejected: list[tuple[int, int, int, int, int, bytes]] = []
        for comp in comps:
            fill = comp[4] / max(1, comp[2] * comp[3])
            if not _arrow_sized(comp, band.width, band.height, fill):
                if comp[4] >= 40:
                    rejected.append((*comp[:4], comp[4], _patch(band, comp, ink_is_light)))
                continue
            patch = _patch(band, comp, ink_is_light)
            direction = _classify(comp, patch, memory)
            if direction is None:
                low_confidence = True
                rejected.append((*comp[:4], comp[4], patch))
                continue
            hits.append(
                _Hit(
                    x=comp[0],
                    y=comp[1] + top,
                    width=comp[2],
                    height=comp[3],
                    direction=direction,
                    patch=patch,
                )
            )
        chosen = _choose_run(hits)
        if not chosen:
            rows.append(_Row((), [], None, (0, top, width, bottom)))
            continue
        first_x = min(hit.x for hit in chosen)
        icon = _icon_patch(rejected, first_x)
        name_right = max(0, first_x - 2)
        name_box = (0, top, name_right, bottom) if name_right >= 8 else None
        rows.append(_Row(tuple(hit.direction for hit in chosen), chosen, icon, name_box))
    return rows, low_confidence


def _classify(comp: tuple[int, int, int, int, int, bytearray], patch: bytes, memory: ShapeMemory) -> str | None:
    del comp
    if not memory.has_glyphs():
        return None
    direction, score = memory.nearest(patch)
    if score >= MIN_NCC:
        return direction
    return None


def _add_cluster(clusters: list[GlyphCluster], patch: bytes) -> None:
    for cluster in clusters:
        if _ncc(patch, cluster.patch) >= CLUSTER_NCC:
            cluster.count += 1
            return
    clusters.append(GlyphCluster(patch, 1))


def _catalog_match(
    code: tuple[str, ...],
    icon: bytes | None,
    memory: ShapeMemory,
    catalog: tuple[Stratagem, ...] | list[Stratagem],
) -> Stratagem | None:
    matches = [item for item in catalog if tuple(item.code) == code]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1 and icon is not None:
        return memory.match_icon(icon, matches)
    return None


def _arrow_patches(prepared: Image.Image) -> list[bytes]:
    patches: list[bytes] = []
    for run, _icon in _component_runs(prepared, arrow_runs_only=False):
        for box in run:
            patches.append(box.patch)
    return patches


def _runs(prepared: Image.Image) -> list[tuple[list[_Hit], bytes | None]]:
    return _component_runs(prepared, arrow_runs_only=True)


def _component_runs(prepared: Image.Image, *, arrow_runs_only: bool) -> list[tuple[list[_Hit], bytes | None]]:
    gray = prepared.convert("L")
    width, height = gray.size
    found: list[tuple[list[_Hit], bytes | None]] = []
    for top, bottom in _bands(_mask(gray)[0], width, height):
        band = gray.crop((0, top, width, bottom))
        mask, ink_is_light = _mask(band)
        comps = _components(mask, band.width, band.height)
        hits: list[_Hit] = []
        rejected: list[tuple[int, int, int, int, int, bytes]] = []
        for comp in comps:
            fill = comp[4] / max(1, comp[2] * comp[3])
            patch = _patch(band, comp, ink_is_light)
            if not _arrow_sized(comp, band.width, band.height, fill):
                if comp[4] >= 40:
                    rejected.append((*comp[:4], comp[4], patch))
                continue
            hits.append(
                _Hit(
                    x=comp[0],
                    y=comp[1] + top,
                    width=comp[2],
                    height=comp[3],
                    direction="",
                    patch=patch,
                )
            )
        if not hits:
            continue
        if arrow_runs_only:
            chosen = _choose_run(hits)
            if not chosen:
                continue
            kept = chosen
        else:
            kept = hits
        first_x = min(hit.x for hit in kept)
        found.append((kept, _icon_patch(rejected, first_x)))
    return found


def _choose_run(hits: list[_Hit]) -> list[_Hit]:
    if not hits:
        return []
    ordered = sorted(hits, key=lambda hit: hit.x)
    heights = sorted(hit.height for hit in ordered)
    widths = sorted(hit.width for hit in ordered)
    median_h = heights[len(heights) // 2]
    median_w = widths[len(widths) // 2]
    groups: list[list[_Hit]] = [[ordered[0]]]
    for hit in ordered[1:]:
        previous = groups[-1][-1]
        gap = hit.x - (previous.x + previous.width)
        similar = abs(hit.height - median_h) <= median_h * 0.5 and abs(hit.width - median_w) <= max(4, median_w * 0.6)
        if similar and -2 <= gap <= max(8, int(median_w * 1.8)):
            groups[-1].append(hit)
        else:
            groups.append([hit])
    valid = [group for group in groups if MIN_ARROWS <= len(group) <= MAX_ARROWS]
    if not valid:
        return []
    valid.sort(key=lambda group: (len(group), group[0].x))
    return valid[-1]


def _icon_patch(rejected: list[tuple[int, int, int, int, int, bytes]], first_arrow_x: int) -> bytes | None:
    left_of_arrows = [item for item in rejected if item[0] + item[2] < first_arrow_x - 2]
    if not left_of_arrows:
        return None
    left_of_arrows.sort(key=lambda item: item[4], reverse=True)
    return left_of_arrows[0][5]


def _arrow_sized(comp: tuple[int, int, int, int, int, bytearray], band_w: int, band_h: int, fill: float) -> bool:
    _x, _y, width, height, _area, _bits = comp
    if width < 6 or height < 8:
        return False
    if height > band_h or width > max(band_w * 0.45, height * 2.2):
        return False
    ratio = width / height
    if not 0.45 <= ratio <= 2.2:
        return False
    return 0.28 <= fill <= 0.78


def _bands(mask: bytearray, width: int, height: int) -> list[tuple[int, int]]:
    if width < 1 or height < 1:
        return []
    counts = [sum(mask[y * width : (y + 1) * width]) for y in range(height)]
    threshold = max(3.0, width * 0.008)
    raw: list[tuple[int, int]] = []
    start: int | None = None
    for y, count in enumerate(counts):
        if count >= threshold:
            if start is None:
                start = y
        elif start is not None:
            raw.append((start, y))
            start = None
    if start is not None:
        raw.append((start, height))
    merged: list[tuple[int, int]] = []
    for top, bottom in raw:
        if merged and top - merged[-1][1] <= 4:
            merged[-1] = (merged[-1][0], bottom)
        else:
            merged.append((top, bottom))
    return [(top, bottom) for top, bottom in merged if bottom - top >= 8]


def _components(mask: bytearray, width: int, height: int) -> list[tuple[int, int, int, int, int, bytearray]]:
    seen = bytearray(width * height)
    found: list[tuple[int, int, int, int, int, bytearray]] = []
    total = width * height
    for start in range(total):
        if not mask[start] or seen[start]:
            continue
        stack = [start]
        seen[start] = 1
        pixels: list[int] = []
        min_x = max_x = start % width
        min_y = max_y = start // width
        while stack:
            point = stack.pop()
            x = point % width
            y = point // width
            pixels.append(point)
            if x < min_x:
                min_x = x
            elif x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            elif y > max_y:
                max_y = y
            if x > 0:
                _push(mask, seen, stack, point - 1)
            if x + 1 < width:
                _push(mask, seen, stack, point + 1)
            if y > 0:
                _push(mask, seen, stack, point - width)
            if y + 1 < height:
                _push(mask, seen, stack, point + width)
        area = len(pixels)
        if area < 40:
            continue
        comp_w = max_x - min_x + 1
        comp_h = max_y - min_y + 1
        bits = bytearray(comp_w * comp_h)
        for point in pixels:
            local_x = point % width - min_x
            local_y = point // width - min_y
            bits[local_y * comp_w + local_x] = 1
        found.append((min_x, min_y, comp_w, comp_h, area, bits))
    return found


def _push(mask: bytearray, seen: bytearray, stack: list[int], point: int) -> None:
    if mask[point] and not seen[point]:
        seen[point] = 1
        stack.append(point)


def _mask(gray: Image.Image) -> tuple[bytearray, bool]:
    raw = gray.tobytes()
    total = len(raw)
    hist = [0] * 256
    for pixel in raw:
        hist[pixel] += 1
    threshold = _otsu(hist, total)
    dark = sum(hist[: threshold + 1])
    ink_is_light = (total - dark) <= dark
    mask = bytearray(total)
    if ink_is_light:
        for index, pixel in enumerate(raw):
            if pixel > threshold:
                mask[index] = 1
    else:
        for index, pixel in enumerate(raw):
            if pixel <= threshold:
                mask[index] = 1
    return mask, ink_is_light


def _otsu(hist: list[int], total: int) -> int:
    if total <= 0:
        return 0
    sum_all = sum(index * count for index, count in enumerate(hist))
    sum_background = 0
    weight_background = 0
    best = -1.0
    threshold = 0
    for index, count in enumerate(hist):
        weight_background += count
        if weight_background == 0:
            continue
        weight_foreground = total - weight_background
        if weight_foreground == 0:
            break
        sum_background += index * count
        mean_background = sum_background / weight_background
        mean_foreground = (sum_all - sum_background) / weight_foreground
        variance = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
        if variance > best:
            best = variance
            threshold = index
    return threshold


def _patch(gray: Image.Image, comp: tuple[int, int, int, int, int, bytearray], ink_is_light: bool) -> bytes:
    crop = gray.crop((comp[0], comp[1], comp[0] + comp[2], comp[1] + comp[3]))
    resized = crop.resize((PATCH, PATCH), Image.Resampling.BOX)
    raw = resized.tobytes()
    if not ink_is_light:
        raw = bytes(255 - pixel for pixel in raw)
    low = min(raw)
    high = max(raw)
    span = high - low
    if span < 8:
        return raw
    return bytes(min(255, (pixel - low) * 255 // span) for pixel in raw)


def _edge_mean(values: list[int], *, start: bool) -> float:
    count = max(1, len(values) // 3)
    chunk = values[:count] if start else values[-count:]
    return sum(chunk) / len(chunk)


def _ncc(left: bytes, right: bytes) -> float:
    count = len(left)
    if count == 0 or count != len(right):
        return -1.0
    mean_left = sum(left) / count
    mean_right = sum(right) / count
    numerator = 0.0
    energy_left = 0.0
    energy_right = 0.0
    for a, b in zip(left, right, strict=True):
        delta_left = a - mean_left
        delta_right = b - mean_right
        numerator += delta_left * delta_right
        energy_left += delta_left * delta_left
        energy_right += delta_right * delta_right
    denom = math.sqrt(energy_left * energy_right)
    if denom < 1e-6:
        if energy_left < 1e-6 and energy_right < 1e-6:
            return 1.0 if abs(mean_left - mean_right) < 8 else 0.0
        return 0.0
    return numerator / denom


def _encode_patch(sample: bytes) -> str:
    return base64.b64encode(sample).decode("ascii")


def _decode_patch(sample: str) -> bytes | None:
    try:
        raw = base64.b64decode(sample, validate=True)
    except (ValueError, TypeError):
        return None
    if len(raw) != PATCH_BYTES:
        return None
    return raw


def _preview_text(rows: list[_Row]) -> str:
    codes = [" ".join(row.code) for row in rows if row.code]
    if not codes:
        return "No arrow glyphs segmented."
    return "\n".join(codes)


def _draw_preview(prepared: Image.Image, rows: list[_Row]) -> Image.Image:
    hits = [hit for row in rows for hit in row.hits]
    base = prepared.convert("RGB")
    if not hits:
        canvas = base.copy()
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 8), "No arrow glyphs segmented.", fill=(255, 233, 0))
        return canvas
    scale = 3
    cell = PATCH * scale
    strip_h = cell + 22
    width = max(base.width, 8 + len(hits) * (cell + 8))
    canvas = Image.new("RGB", (width, base.height + strip_h), (8, 8, 8))
    canvas.paste(base, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for hit in hits:
        draw.rectangle(
            (hit.x, hit.y, hit.x + hit.width - 1, hit.y + hit.height - 1),
            outline=(255, 233, 0),
            width=2,
        )
        draw.text((hit.x, max(0, hit.y - 12)), hit.direction, fill=(255, 233, 0), font=font)
    for index, hit in enumerate(hits):
        patch = Image.frombytes("L", (PATCH, PATCH), hit.patch).resize((cell, cell), Image.Resampling.NEAREST)
        x = 8 + index * (cell + 8)
        y = base.height + 4
        canvas.paste(patch.convert("RGB"), (x, y))
        draw.text((x, y + cell + 1), hit.direction, fill=(255, 233, 0), font=font)
    return canvas
