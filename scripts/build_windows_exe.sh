#!/usr/bin/env bash
# Build HelldiversStratagemWheel.exe on Linux.
# pynsist stages official Windows CPython and wheels. NSIS packs a PE
# launcher. PyInstaller cannot cross-compile, so it is not used.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="$ROOT/.venv/bin/python"
PYNSIST="$ROOT/.venv/bin/pynsist"
CACHE="$ROOT/build/cache"
WHEELS="$ROOT/build/wheels"
STAGED="$ROOT/build/nsis"
PAYLOAD="$ROOT/build/windows/payload"
OUT="$ROOT/build/windows/HelldiversStratagemWheel.exe"
MEDIA="/cursor/stores/bc-e8591809-38be-4c71-a896-fedcb60eabc2/media/HelldiversStratagemWheel.exe"
PY_VERSION="3.12.10"
APP_VERSION="1.0.2"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing '$1'. Install it and run this script again." >&2
    exit 1
  fi
}

need curl
need 7z
need makensis
need msiextract
test -x "$PY"
test -x "$PYNSIST"

mkdir -p "$CACHE" "$WHEELS" "$ROOT/build/windows" "$ROOT/packaging"

"$PY" - << 'PY'
from PIL import Image, ImageDraw
from pathlib import Path
icon = Image.new("RGB", (64, 64), "#111111")
draw = ImageDraw.Draw(icon)
draw.rectangle((3, 3, 60, 60), outline="#FFE900", width=4)
draw.polygon([(32, 14), (50, 32), (32, 50), (14, 32)], outline="#FFE900")
draw.polygon([(32, 22), (42, 32), (32, 42), (22, 32)], fill="#FFE900")
path = Path("build/app.ico")
path.parent.mkdir(parents=True, exist_ok=True)
icon.save(path, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
PY

TCLTK_MSI="$CACHE/tcltk-${PY_VERSION}.msi"
if [[ ! -s "$TCLTK_MSI" ]]; then
  curl -fL --retry 3 -o "$TCLTK_MSI" \
    "https://www.python.org/ftp/python/${PY_VERSION}/amd64/tcltk.msi"
fi

TESS_EXE="$CACHE/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
if [[ ! -s "$TESS_EXE" ]]; then
  curl -fL --retry 3 -o "$TESS_EXE" \
    "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
fi

rm -rf "$WHEELS"
mkdir -p "$WHEELS"
# --no-deps: pynput's evdev extra is Linux-only and has no Windows wheel.
# Windows needs the pure pynput wheel plus six. pytesseract needs packaging.
"$PY" -m pip download \
  --dest "$WHEELS" \
  --no-deps \
  --only-binary=:all: \
  --platform win_amd64 \
  --python-version 3.12 \
  --implementation cp \
  pynput \
  six \
  mss \
  pytesseract \
  packaging \
  rapidfuzz \
  Pillow

export PYTHONPATH="$ROOT"
"$PYNSIST" "$ROOT/packaging/installer.cfg" --no-makensis

rm -rf "$PAYLOAD"
mkdir -p "$PAYLOAD"
cp -a "$STAGED/Python" "$PAYLOAD/Python"
cp -a "$STAGED/pkgs" "$PAYLOAD/pkgs"
cp -a "$STAGED/Stratagem_Terminal.launch.pyw" "$PAYLOAD/Stratagem_Terminal.launch.pyw"
"$PY" - "$PAYLOAD" << 'PY'
import shutil
import sys
from pathlib import Path
for path in Path(sys.argv[1]).rglob("__pycache__"):
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
PY

if grep -q -- '--demo' "$PAYLOAD/Stratagem_Terminal.launch.pyw"; then
  echo "Launcher must start live mode, without --demo." >&2
  exit 1
fi

TCLTK="$CACHE/tcltk-${PY_VERSION}"
rm -rf "$TCLTK"
mkdir -p "$TCLTK"
msiextract --directory "$TCLTK" "$TCLTK_MSI" >/dev/null

PYDIR="$PAYLOAD/Python"
mkdir -p "$PYDIR/DLLs" "$PYDIR/Lib"
cp -a "$TCLTK/DLLs/_tkinter.pyd" "$PYDIR/_tkinter.pyd"
cp -a "$TCLTK/DLLs/_tkinter.pyd" "$PYDIR/DLLs/_tkinter.pyd"
cp -a "$TCLTK/DLLs/tcl86t.dll" "$TCLTK/DLLs/tk86t.dll" "$TCLTK/DLLs/zlib1.dll" "$PYDIR/"
cp -a "$TCLTK/DLLs/tcl86t.dll" "$TCLTK/DLLs/tk86t.dll" "$TCLTK/DLLs/zlib1.dll" "$PYDIR/DLLs/"
rm -rf "$PYDIR/tcl"
mkdir -p "$PYDIR/tcl"
cp -a "$TCLTK/tcl/tcl8.6" "$TCLTK/tcl/tk8.6" "$TCLTK/tcl/dde1.4" "$TCLTK/tcl/reg1.3" "$PYDIR/tcl/"
rm -rf "$PYDIR/tcl/tk8.6/demos"
rm -rf "$PYDIR/Lib/tkinter"
cp -a "$TCLTK/Lib/tkinter" "$PYDIR/Lib/tkinter"

PTH="$(echo "$PYDIR"/python*._pth)"
if ! grep -q '^DLLs' "$PTH"; then
  printf '\r\nDLLs\r\nLib\r\n' >> "$PTH"
fi
if ! grep -q 'import site' "$PTH"; then
  echo "Embeddable Python pth is missing 'import site'." >&2
  exit 1
fi

TESS_RAW="$CACHE/tesseract-extract"
rm -rf "$TESS_RAW"
mkdir -p "$TESS_RAW"
# 7-Zip matches these NSIS paths with forward slashes. A leading
# wildcard does not match tessdata/eng.traineddata and still exits 0.
7z x -y -o"$TESS_RAW" "$TESS_EXE" \
  tesseract.exe \
  '*.dll' \
  'tessdata/eng.traineddata' \
  'tessdata/eng.user-words' \
  'tessdata/eng.user-patterns' \
  >/dev/null

rm -rf "$PAYLOAD/tesseract"
mkdir -p "$PAYLOAD/tesseract/tessdata"
cp -a "$TESS_RAW/tesseract.exe" "$PAYLOAD/tesseract/tesseract.exe"
cp -a "$TESS_RAW"/*.dll "$PAYLOAD/tesseract/"
trained="$(find "$TESS_RAW" -type f -name 'eng.traineddata' -print -quit)"
if [[ -z "$trained" ]]; then
  echo "UB Mannheim installer did not contain eng.traineddata" >&2
  exit 1
fi
cp -a "$trained" "$PAYLOAD/tesseract/tessdata/eng.traineddata"
words="$(find "$TESS_RAW" -type f -name 'eng.user-words' -print -quit || true)"
patterns="$(find "$TESS_RAW" -type f -name 'eng.user-patterns' -print -quit || true)"
if [[ -n "$words" && -n "$patterns" ]]; then
  cp -a "$words" "$patterns" "$PAYLOAD/tesseract/tessdata/"
fi
# Tesseract's own DLLs load the VC runtime from their directory.
for runtime_dll in vcruntime140.dll vcruntime140_1.dll; do
  if [[ -f "$PYDIR/$runtime_dll" && ! -f "$PAYLOAD/tesseract/$runtime_dll" ]]; then
    cp -a "$PYDIR/$runtime_dll" "$PAYLOAD/tesseract/$runtime_dll"
  fi
done

test -f "$PAYLOAD/tesseract/tesseract.exe"
test -f "$PAYLOAD/tesseract/tessdata/eng.traineddata"
# A real UB Mannheim eng.traineddata is a few megabytes. A failed 7z
# extract can leave a tiny stub that still passes test -f.
trained_bytes="$(wc -c < "$PAYLOAD/tesseract/tessdata/eng.traineddata")"
if [[ "$trained_bytes" -lt 1000000 ]]; then
  echo "eng.traineddata is only ${trained_bytes} bytes." >&2
  exit 1
fi
echo "staged payload tesseract/tessdata/eng.traineddata (${trained_bytes} bytes)"
test -f "$PYDIR/pythonw.exe"
test -f "$PYDIR/Lib/tkinter/__init__.py"
test -f "$PYDIR/tcl/tcl8.6/init.tcl"
test -f "$PAYLOAD/pkgs/stratagems/__main__.py"

"$PY" - "$PAYLOAD" << 'PY'
import struct
import sys
from pathlib import Path

payload = Path(sys.argv[1])
SYSTEM = {
    "kernel32.dll", "user32.dll", "gdi32.dll", "advapi32.dll", "shell32.dll",
    "ole32.dll", "oleaut32.dll", "comctl32.dll", "comdlg32.dll", "imm32.dll",
    "ws2_32.dll", "netapi32.dll", "userenv.dll", "ntdll.dll", "shlwapi.dll",
    "setupapi.dll", "winmm.dll", "winspool.drv", "crypt32.dll", "bcrypt.dll",
    "secur32.dll", "iphlpapi.dll", "rpcrt4.dll", "msvcrt.dll", "version.dll",
    "uxtheme.dll", "dwmapi.dll", "mpr.dll", "netutils.dll", "wldap32.dll",
    "normaliz.dll", "psapi.dll", "imagehlp.dll", "dbghelp.dll", "cabinet.dll",
    "powrprof.dll", "propsys.dll", "dnsapi.dll", "nsi.dll", "sspicli.dll",
    "kernelbase.dll", "ucrtbase.dll", "msvcp140.dll", "msvcp140_1.dll",
    "concrt140.dll", "vcomp140.dll", "sechost.dll", "combase.dll",
    "msimg32.dll", "usp10.dll", "dwrite.dll", "gdiplus.dll", "oleacc.dll",
    "winhttp.dll", "wintrust.dll", "d3d11.dll", "dxgi.dll", "opengl32.dll",
    "glu32.dll", "wsock32.dll", "mswsock.dll", "cryptbase.dll", "msi.dll",
}

def imports(path: Path) -> list[str]:
    data = path.read_bytes()
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    coff = e_lfanew + 4
    _machine, nsec, _t, _s, _p, optsize, _c = struct.unpack_from("<HHIIIHH", data, coff)
    opt = coff + 20
    magic = struct.unpack_from("<H", data, opt)[0]
    dd_off = opt + (112 if magic == 0x20B else 96)
    import_rva, _import_size = struct.unpack_from("<II", data, dd_off + 8)
    if import_rva == 0:
        return []
    sections = []
    sec_off = opt + optsize
    for index in range(nsec):
        off = sec_off + index * 40
        vsize, va, rsize, raw = struct.unpack_from("<IIII", data, off + 8)
        sections.append((va, max(vsize, rsize), raw))

    def rva_to_off(rva: int) -> int:
        for va, span, raw in sections:
            if va <= rva < va + span:
                return raw + (rva - va)
        raise KeyError(rva)

    off = rva_to_off(import_rva)
    names = []
    while True:
        _ilt, _time, _fwd, name_rva, _iat = struct.unpack_from("<IIIII", data, off)
        if name_rva == 0:
            break
        start = rva_to_off(name_rva)
        end = data.index(b"\0", start)
        names.append(data[start:end].decode("ascii", "replace"))
        off += 20
    return names

def check(folder: Path, also_present: set[str] | None = None) -> None:
    present = {path.name.casefold() for path in folder.iterdir() if path.is_file()}
    if also_present:
        present |= also_present
    missing = []
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.casefold() not in {".dll", ".exe", ".pyd"}:
            continue
        for name in imports(path):
            key = name.casefold()
            if key.startswith("api-ms-win-"):
                continue
            if key in SYSTEM or key in present:
                continue
            missing.append(f"{path.name} -> {name}")
    if missing:
        print("\n".join(missing), file=sys.stderr)
        raise SystemExit(f"Missing DLLs under {folder}")

check(payload / "tesseract")
python_dir = payload / "Python"
check(python_dir)
dll_dir = python_dir / "DLLs"
if dll_dir.is_dir():
    parent_files = {path.name.casefold() for path in python_dir.iterdir() if path.is_file()}
    check(dll_dir, parent_files)
print("PE import closure ok")
PY

rm -f "$OUT"
makensis -NOCD \
  -DPAYLOAD="$PAYLOAD" \
  -DOUTFILE="$OUT" \
  -DICON="$ROOT/build/app.ico" \
  -DAPP_VERSION="$APP_VERSION" \
  "$ROOT/packaging/portable.nsi"

if ! 7z l "$OUT" | grep -F 'tesseract/tessdata/eng.traineddata'; then
  echo "Installer is missing tesseract/tessdata/eng.traineddata" >&2
  exit 1
fi
file "$OUT"
mkdir -p "$(dirname "$MEDIA")"
cp -f "$OUT" "$MEDIA"
file "$MEDIA"
ls -l "$MEDIA"
