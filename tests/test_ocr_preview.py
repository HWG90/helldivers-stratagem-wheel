from PIL import Image

from stratagems.hdr import HdrCurve
from stratagems.ocr import lines_from_image, ocr_bitmap, preprocess


def test_preview_bitmap_matches_tesseract_buffer(monkeypatch) -> None:
    sent: list[Image.Image] = []
    built: list[Image.Image] = []
    real_bitmap = ocr_bitmap

    def spy_bitmap(image: Image.Image, *, hdr: bool = False, curve: HdrCurve | None = None) -> Image.Image:
        result = real_bitmap(image, hdr=hdr, curve=curve)
        built.append(result)
        return result

    def fake_image_to_data(image: Image.Image, **_kwargs: object) -> dict[str, list[object]]:
        sent.append(image)
        return {"text": [], "conf": [], "block_num": [], "par_num": [], "line_num": []}

    monkeypatch.setattr("stratagems.ocr.ocr_bitmap", spy_bitmap)
    monkeypatch.setattr("stratagems.ocr.pytesseract.image_to_data", fake_image_to_data)

    crop = Image.new("RGB", (48, 28), (16, 18, 20))
    for x in range(48):
        for y in range(8):
            crop.putpixel((x, y), (96, 98, 94))
    curve = HdrCurve(exposure_stops=1.2, gamma=0.75, contrast=1.5, black_level=0.06)

    for hdr in (False, True):
        sent.clear()
        built.clear()
        preview = real_bitmap(crop, hdr=hdr, curve=curve)
        lines_from_image(crop, hdr=hdr, curve=curve)
        assert len(sent) == 1
        assert len(built) == 1
        assert sent[0] is built[0]
        assert sent[0].mode == preview.mode
        assert sent[0].size == preview.size
        assert sent[0].tobytes() == preview.tobytes()

    untouched = preprocess(crop)
    assert real_bitmap(crop, hdr=False, curve=curve).tobytes() == untouched.tobytes()
