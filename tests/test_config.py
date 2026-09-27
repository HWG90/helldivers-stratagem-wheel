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
    payload = json.loads(json.dumps(Config().to_dict()))
    assert payload["gap_ms"] == 50
    assert payload["hdr"] is False
    assert payload["hdr_exposure"] == 0.0
    assert payload["hdr_gamma"] == 1.0
    assert payload["hdr_contrast"] == 1.0
    assert payload["hdr_black_level"] == 0.0


def test_hdr_settings_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    saved = Config(
        hdr=True,
        hdr_exposure=1.25,
        hdr_gamma=0.85,
        hdr_contrast=1.4,
        hdr_black_level=0.12,
        region=Region(1, 2, 3, 4),
    )
    save_config(saved)
    loaded, warning = load_config()
    assert warning is None
    assert loaded.hdr is True
    assert loaded.hdr_exposure == 1.25
    assert loaded.hdr_gamma == 0.85
    assert loaded.hdr_contrast == 1.4
    assert loaded.hdr_black_level == 0.12
    assert loaded.region == Region(1, 2, 3, 4)


def test_old_config_without_hdr_stays_off(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = config_path()
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"radial_bind": "f6"}), encoding="utf-8")
    loaded, warning = load_config()
    assert warning is None
    assert loaded.radial_bind == "f6"
    assert loaded.hdr is False
    assert loaded.hdr_exposure == 0.0
    assert loaded.hdr_gamma == 1.0
    assert loaded.hdr_contrast == 1.0
    assert loaded.hdr_black_level == 0.0


def test_hdr_values_are_clamped(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = config_path()
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "hdr": "yes",
                "hdr_exposure": 99,
                "hdr_gamma": 0,
                "hdr_contrast": -2,
                "hdr_black_level": 4,
            }
        ),
        encoding="utf-8",
    )
    loaded, warning = load_config()
    assert warning is None
    assert loaded.hdr is False
    assert loaded.hdr_exposure == 4.0
    assert loaded.hdr_gamma == 0.2
    assert loaded.hdr_contrast == 0.25
    assert loaded.hdr_black_level == 0.95
