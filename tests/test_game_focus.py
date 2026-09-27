"""The radial bind opens the wheel only while Helldivers 2 is focused."""

from stratagems.app import App
from stratagems.game_focus import helldivers_focused, is_helldivers_process
from stratagems.pointer_lock import PointerLock


def test_process_name_matches_the_game_executable() -> None:
    assert is_helldivers_process(r"C:\Program Files\Helldivers 2\bin\helldivers2.exe")
    assert is_helldivers_process("HELLDIVERS2.EXE")
    assert not is_helldivers_process(r"C:\Games\helldivers2_helper.exe")
    assert not is_helldivers_process("steam.exe")
    assert not is_helldivers_process(None)
    assert not is_helldivers_process("")


def test_non_windows_foreground_is_not_the_game() -> None:
    assert helldivers_focused() is False


def test_radial_bind_stays_closed_until_the_game_is_focused(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    app = App(demo=True)
    cursor = {"x": 400, "y": 300}
    fired: list[str] = []
    try:
        app._lock = PointerLock(
            lambda: (cursor["x"], cursor["y"]),
            lambda x, y: cursor.update(x=x, y=y),
        )
        app._fire = lambda entry: fired.append(entry.name)
        app._game_focused = lambda: False

        app._from_mouse("mouse3", True, 400, 300)
        app.root.update()
        assert not app._lock.active
        assert not app.overlay.visible
        assert not app._radial_down

        app._game_focused = lambda: True
        app._from_mouse("mouse3", True, 400, 300)
        app.root.update()
        assert app._lock.active
        assert app._radial_down
        assert app.overlay.visible

        app.overlay.apply_offset(200, 0)
        app._game_focused = lambda: False
        app._from_move(460, 300)
        app.root.update()
        assert fired == []
        assert not app.overlay.visible
        assert not app._lock.active
        assert not app._radial_down

        app.preview()
        assert app.overlay.visible
        assert not app._lock.active
    finally:
        app.root.destroy()
