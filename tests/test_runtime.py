import os
from pathlib import Path

import pytesseract

import stratagems.runtime as runtime
from stratagems.runtime import locate_tcl_tk, locate_tesseract, tesseract_config


def test_locate_tesseract_next_to_app(tmp_path: Path) -> None:
    folder = tmp_path / "tesseract"
    (folder / "tessdata").mkdir(parents=True)
    (folder / "tesseract.exe").write_bytes(b"MZ")
    (folder / "tessdata" / "eng.traineddata").write_bytes(b"trained")

    found = locate_tesseract([tmp_path])

    assert found is not None
    exe, tessdata = found
    assert exe == folder / "tesseract.exe"
    assert tessdata == folder / "tessdata"


def test_locate_tesseract_requires_english_data(tmp_path: Path) -> None:
    folder = tmp_path / "tesseract"
    folder.mkdir()
    (folder / "tesseract.exe").write_bytes(b"MZ")

    assert locate_tesseract([tmp_path]) is None


def test_locate_tcl_tk_under_python_dir(tmp_path: Path) -> None:
    tcl_dir = tmp_path / "Python" / "tcl" / "tcl8.6"
    tk_dir = tmp_path / "Python" / "tcl" / "tk8.6"
    tcl_dir.mkdir(parents=True)
    tk_dir.mkdir(parents=True)
    (tcl_dir / "init.tcl").write_text("", encoding="utf-8")
    (tk_dir / "tk.tcl").write_text("", encoding="utf-8")

    assert locate_tcl_tk([tmp_path]) == (tcl_dir, tk_dir)


def test_configure_points_at_bundled_tesseract(tmp_path: Path, monkeypatch) -> None:
    folder = tmp_path / "tesseract" / "tessdata"
    folder.mkdir(parents=True)
    exe = tmp_path / "tesseract" / "tesseract.exe"
    exe.write_bytes(b"MZ")
    (folder / "eng.traineddata").write_bytes(b"trained")
    monkeypatch.setattr(runtime, "_CONFIGURED", False)
    monkeypatch.setattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    monkeypatch.delenv("HELLDIVERS_TESSDATA", raising=False)
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)

    runtime.configure_bundled_runtime([tmp_path])

    assert pytesseract.pytesseract.tesseract_cmd == str(exe)
    assert Path(os.environ["HELLDIVERS_TESSDATA"]) == folder
    assert "--tessdata-dir" in tesseract_config()
    assert str(folder) in tesseract_config()
