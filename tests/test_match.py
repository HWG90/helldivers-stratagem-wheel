from stratagems.catalog import STRATAGEMS, get, sample_loadout
from stratagems.matching import best_match, resolve_line, resolve_lines

# Published infobox codes, Helldivers Wiki, retrieved 2026-09-26.
PUBLISHED = {
    "Reinforce": ("up", "down", "right", "left", "up"),
    "Resupply": ("down", "down", "up", "right"),
    "SoS Beacon": ("up", "down", "right", "up"),
    "NUX-223 Hellbomb": ("down", "up", "left", "down", "up", "right", "down", "up"),
    "SEAF Artillery": ("right", "up", "up", "down"),
    "Eagle Rearm": ("up", "up", "left", "up", "right"),
    "Eagle Airstrike": ("up", "right", "down", "right"),
    "Eagle 500kg Bomb": ("up", "right", "down", "down", "down"),
    "Orbital Precision Strike": ("right", "right", "up"),
    "Orbital Gatling Barrage": ("right", "down", "left", "up", "up"),
    "MG-43 Machine Gun": ("down", "left", "down", "up", "right"),
    "E/MG-101 HMG Emplacement": ("down", "up", "left", "right", "right", "left"),
    "LIFT-850 Jump Pack": ("down", "up", "up", "down", "up"),
}


def test_published_wiki_codes() -> None:
    for name, code in PUBLISHED.items():
        stratagem = get(name)
        assert stratagem is not None, name
        assert stratagem.code == code


def test_catalog_covers_the_common_permits() -> None:
    kinds = {item.kind for item in STRATAGEMS}
    for kind in ("Orbital", "Eagle", "Support Weapon", "Backpack", "Emplacement", "Sentry", "Ship", "Objective"):
        assert kind in kinds
    assert len(STRATAGEMS) >= 80
    assert len(sample_loadout()) == 10


def test_every_catalog_name_matches_itself() -> None:
    for stratagem in STRATAGEMS:
        match = best_match(stratagem.name)
        assert match is not None
        assert match.exact
        assert match.stratagem.name == stratagem.name


def _name(query: str) -> str:
    match = best_match(query)
    assert match is not None, query
    return match.stratagem.name


def test_short_names_and_ocr_noise() -> None:
    assert _name("Machine Gun") == "MG-43 Machine Gun"
    assert _name("Machine Gun Sentry") == "A/MG-43 Machine Gun Sentry"
    assert _name("Autocannon") == "AC-8 Autocannon"
    assert _name("Hellbomb") == "NUX-223 Hellbomb"
    assert _name("SOS") == "SoS Beacon"
    assert _name("500kg") == "Eagle 500kg Bomb"
    assert _name("eag1e airstrike") == "Eagle Airstrike"
    assert _name("Reinforse") == "Reinforce"
    assert best_match("zzzzzzzz") is None
    assert best_match("laser") is None


def test_clean_arrow_glyphs_override_the_table() -> None:
    row = resolve_line("Orbital Precision Strike ↑ ↓")
    assert row is not None
    assert row.name == "Orbital Precision Strike"
    assert row.code == ("up", "down")
    assert row.code_source == "screen"


def test_missing_glyphs_use_the_table() -> None:
    row = resolve_line("Orbital Precision Strike")
    assert row is not None
    assert row.code == ("right", "right", "up")
    assert row.code_source == "table"


def test_arrow_only_follow_line_keeps_the_on_screen_code() -> None:
    rows = resolve_lines(["Eagle Airstrike", "↑ ↑ ↑"])
    assert len(rows) == 1
    assert rows[0].name == "Eagle Airstrike"
    assert rows[0].code == ("up", "up", "up")
    assert rows[0].code_source == "screen"
