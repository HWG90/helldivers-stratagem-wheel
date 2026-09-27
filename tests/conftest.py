"""Keep tests isolated from real user config and active game logs."""
import pytest

@pytest.fixture(autouse=True)
def isolate_user_directories(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
