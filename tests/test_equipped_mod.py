"""Run the current mod fixtures rather than the obsolete memory layout."""
import os
from pathlib import Path
import subprocess
import sys
import pytest

MOD = Path(__file__).resolve().parents[1] / "mods/EquippedStratagems"

def test_mod_package():
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], cwd=MOD, check=True)

@pytest.mark.parametrize("fixture", ["runtime_test.lua", "ffi_smoke.lua"])
def test_mod_lua(fixture):
    if os.name != "nt" or not Path("C:/Program Files (x86)/Steam/steamapps/common/Helldivers 2/bin/lua51.dll").exists():
        pytest.skip("Installed Windows game LuaJIT needed for isolated Lua fixtures")
    subprocess.run([sys.executable, "run_lua.py", "tests/"+fixture], cwd=MOD, check=True)
