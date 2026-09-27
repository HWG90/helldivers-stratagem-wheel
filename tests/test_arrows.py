from stratagems.arrows import merge_orphan_arrow_lines, parse_arrow_glyphs, split_name_and_arrows


def test_spaced_and_glued_unicode_arrows() -> None:
    assert parse_arrow_glyphs("↑ → ↓ →") == ["up", "right", "down", "right"]
    assert parse_arrow_glyphs("↑→↓→") == ["up", "right", "down", "right"]


def test_words_letters_and_ascii_clusters() -> None:
    assert parse_arrow_glyphs("up down right left up") == ["up", "down", "right", "left", "up"]
    assert parse_arrow_glyphs("U D R L U") == ["up", "down", "right", "left", "up"]
    assert parse_arrow_glyphs("^>v>") == ["up", "right", "down", "right"]
    assert parse_arrow_glyphs(">>^") == ["right", "right", "up"]


def test_name_and_arrows_on_the_same_line() -> None:
    name, arrows = split_name_and_arrows("EAGLE AIRSTRIKE ↑ → ↓ →")
    assert name == "EAGLE AIRSTRIKE"
    assert arrows == ["up", "right", "down", "right"]


def test_broken_short_and_long_runs_are_rejected() -> None:
    assert parse_arrow_glyphs("↑ EAGLE →") is None
    assert parse_arrow_glyphs("↑") is None
    assert parse_arrow_glyphs("↑" * 13) is None
    assert parse_arrow_glyphs("MACHINE GUN") is None


def test_orphan_arrow_line_merges_onto_the_name() -> None:
    merged = merge_orphan_arrow_lines(["Eagle Airstrike", "↑ → ↓ →", "Resupply"])
    assert merged == ["Eagle Airstrike ↑ → ↓ →", "Resupply"]
