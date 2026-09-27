"""Locate bundled Windows runtimes next to the app.

The downloadable exe carries CPython, Tcl/Tk, and Tesseract beside the
launcher. This module points the process at those files so a machine
without Python or a system Tesseract install can still open the terminal
and read the stratagem list.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytesseract

_CONFIGURED = False


def search_roots() -> list[Path]:
    """Directories that may hold a bundled ``tesseract`` or ``Python`` folder."""
    roots: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            return
        if resolved in seen:
            return
        seen.add(resolved)
        roots.append(resolved)

    env_dir = os.environ.get("HELLDIVERS_APP_DIR")
    if env_dir:
        add(Path(env_dir))
    executable = Path(sys.executable)
    add(executable.parent)
    add(executable.parent.parent)
    if getattr(sys, "frozen", False):
        add(executable.parent)
    # Source checkout: the repository root is the parent of this package.
    add(Path(__file__).resolve().parent.parent)
    return roots


def locate_tesseract(roots: list[Path]) -> tuple[Path, Path] | None:
    """Return ``(tesseract.exe, tessdata directory)`` when both are present."""
    relative_exes = (
        Path("tesseract") / "tesseract.exe",
        Path("Tesseract-OCR") / "tesseract.exe",
        Path("tesseract.exe"),
    )
    for root in roots:
        for relative in relative_exes:
            exe = root / relative
            if not exe.is_file():
                continue
            tessdata = _tessdata_beside(exe)
            if tessdata is not None:
                return exe, tessdata
    return None


def locate_tcl_tk(roots: list[Path]) -> tuple[Path, Path] | None:
    """Return ``(tcl8.6 directory, tk8.6 directory)`` for a bundled interpreter."""
    relative_pairs = (
        (Path("tcl") / "tcl8.6", Path("tcl") / "tk8.6"),
        (Path("Python") / "tcl" / "tcl8.6", Path("Python") / "tcl" / "tk8.6"),
        (Path("lib") / "tcl8.6", Path("lib") / "tk8.6"),
    )
    for root in roots:
        for tcl_rel, tk_rel in relative_pairs:
            tcl_dir = root / tcl_rel
            tk_dir = root / tk_rel
            if (tcl_dir / "init.tcl").is_file() and (tk_dir / "tk.tcl").is_file():
                return tcl_dir, tk_dir
    return None


def configure_bundled_runtime(roots: list[Path] | None = None) -> None:
    """Point Tcl/Tk and Tesseract at bundled files, when those files exist."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True
    found = search_roots() if roots is None else roots
    _configure_tcl(found)
    _configure_tesseract(found)


def tesseract_config() -> str:
    """Tesseract CLI flags, including a bundled tessdata directory."""
    base = "--psm 6 -l eng"
    tessdata = os.environ.get("HELLDIVERS_TESSDATA")
    if not tessdata:
        return base
    return f'{base} --tessdata-dir "{tessdata}"'


def _tessdata_beside(exe: Path) -> Path | None:
    for folder in (exe.parent / "tessdata", exe.parent.parent / "tessdata"):
        if (folder / "eng.traineddata").is_file():
            return folder
    return None


def _configure_tcl(roots: list[Path]) -> None:
    if os.environ.get("TCL_LIBRARY") and os.environ.get("TK_LIBRARY"):
        return
    located = locate_tcl_tk(roots)
    if located is None:
        return
    tcl_dir, tk_dir = located
    os.environ.setdefault("TCL_LIBRARY", str(tcl_dir))
    os.environ.setdefault("TK_LIBRARY", str(tk_dir))


def _configure_tesseract(roots: list[Path]) -> None:
    located = locate_tesseract(roots)
    if located is None:
        return
    exe, tessdata = located
    # Tesseract 5 treats TESSDATA_PREFIX as the parent of the tessdata folder.
    os.environ["TESSDATA_PREFIX"] = str(tessdata.parent)
    os.environ["HELLDIVERS_TESSDATA"] = str(tessdata)
    pytesseract.pytesseract.tesseract_cmd = str(exe)
