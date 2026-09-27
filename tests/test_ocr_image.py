import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from stratagems.ocr import lines_from_image, scan_image

pytestmark = pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")


def test_high_contrast_list_resolves_names() -> None:
    image = Image.new("RGB", (900, 220), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
    draw.text((20, 30), "RESUPPLY", fill="black", font=font)
    draw.text((20, 110), "EAGLE AIRSTRIKE  UP RIGHT DOWN RIGHT", fill="black", font=font)
    lines = lines_from_image(image)
    blob = " ".join(lines).casefold()
    assert "resupply" in blob
    rows = scan_image(image)
    names = {row.name for row in rows}
    assert "Resupply" in names
    eagle = next(row for row in rows if row.name == "Eagle Airstrike")
    assert eagle.code == ("up", "right", "down", "right")
    assert eagle.code_source == "screen"
