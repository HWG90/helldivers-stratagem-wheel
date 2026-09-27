from PIL import Image, ImageStat

from stratagems.hdr import HdrCurve, apply_hdr, auto_curve, prepare_scan_image


def test_identity_curve_keeps_pixels() -> None:
    image = Image.new("RGB", (2, 2), (12, 34, 56))
    assert apply_hdr(image, HdrCurve()).getpixel((0, 0)) == (12, 34, 56)


def test_flat_gray_exposure_lifts_and_black_crushes() -> None:
    image = Image.new("RGB", (8, 8), (96, 96, 96))
    lifted = apply_hdr(image, HdrCurve(exposure_stops=1))
    assert lifted.getpixel((0, 0)) == (192, 192, 192)
    crushed = apply_hdr(image, HdrCurve(black_level=96 / 255))
    assert crushed.getpixel((3, 3)) == (0, 0, 0)


def test_blown_out_highlights_drop_and_spread() -> None:
    image = Image.new("RGB", (8, 4), (255, 255, 255))
    for x in range(4):
        for y in range(4):
            image.putpixel((x, y), (240, 240, 240))
    adjusted = apply_hdr(image, HdrCurve(exposure_stops=-1, contrast=3))
    assert adjusted.getpixel((0, 0)) == (105, 105, 105)
    assert adjusted.getpixel((7, 0)) == (128, 128, 128)
    assert _span(adjusted) > _span(image)
    assert _mean(adjusted) < _mean(image)
    assert max(adjusted.getpixel((7, 0))) < 200


def test_auto_widens_luminance_range() -> None:
    image = Image.new("RGB", (50, 40), (28, 28, 28))
    for x in range(50):
        for y in range(8):
            image.putpixel((x, y), (76, 76, 76))
    before = _span(image)
    adjusted = apply_hdr(image, auto_curve(image))
    panel = adjusted.getpixel((0, 39))[0]
    text = adjusted.getpixel((0, 0))[0]
    assert _span(adjusted) > before * 2
    assert text > panel
    assert text >= 180
    assert panel <= 40


def test_prepare_scan_skips_curve_when_hdr_is_off() -> None:
    image = Image.new("RGB", (4, 4), (40, 40, 40))
    curve = HdrCurve(exposure_stops=2)
    assert prepare_scan_image(image, enabled=False, curve=curve) is image
    adjusted = prepare_scan_image(image, enabled=True, curve=curve)
    assert adjusted.getpixel((0, 0)) != (40, 40, 40)


def _span(image: Image.Image) -> int:
    low, high = image.convert("L").getextrema()
    return int(high) - int(low)


def _mean(image: Image.Image) -> float:
    return float(ImageStat.Stat(image.convert("L")).mean[0])
