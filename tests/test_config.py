import json

from stratagems.calibrate import display_rect_to_screen
from stratagems.config import Config, Region, config_path, load_config, save_config


def test_config_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    saved = Config(
        radial_bind="mouse5",
        rescan_bind="f8",
        direction_style="wasd",
        pinned=["Reinforce", "Not A Real Stratagem"],
        region=Region(10, 20, 300, 400),
        start_delay_ms=80,
    )
    # Unknown pins are dropped on load, not on save.
    path = save_config(saved)
    assert path == config_path()
    loaded, warning = load_config()
    assert warning is None
    assert loaded.radial_bind == "mouse5"
    assert loaded.direction_style == "wasd"
    assert loaded.region == Region(10, 20, 300, 400)
    assert loaded.pinned == ["Reinforce"]
    assert loaded.start_delay_ms == 80


def test_corrupt_config_falls_back(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = config_path()
    path.parent.mkdir(parents=True)
    path.write_text("{", encoding="utf-8")
    loaded, warning = load_config()
    assert loaded.radial_bind == "mouse3"
    assert warning is not None
    assert not path.exists()


def test_display_rect_scales_to_screen_coordinates() -> None:
    region = display_rect_to_screen(10, 20, 110, 220, scale=0.5, origin_x=100, origin_y=50)
    assert region == Region(120, 90, 200, 400)
    flipped = display_rect_to_screen(110, 220, 10, 20, scale=0.5, origin_x=0, origin_y=0)
    assert flipped == Region(20, 40, 200, 400)


def test_saved_json_is_plain() -> None:
    assert json.loads(json.dumps(Config().to_dict()))["gap_ms"] == 50
