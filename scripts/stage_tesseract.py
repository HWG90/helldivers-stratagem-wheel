"""Copy the Tesseract runtime a Windows scan needs, without debug sections.

The name fallback uses tesseract.exe and eng.traineddata only after
Windows.Media.Ocr and RapidOCR both return nothing. UB Mannheim's
libtesseract DLL ships about 80 MB of DWARF debug data. That is stripped
here so the installer can still carry tessdata.
"""

from __future__ import annotations

import shutil
import struct
import sys
from pathlib import Path

SYSTEM = {
    "kernel32.dll",
    "user32.dll",
    "gdi32.dll",
    "advapi32.dll",
    "shell32.dll",
    "ole32.dll",
    "oleaut32.dll",
    "comctl32.dll",
    "comdlg32.dll",
    "imm32.dll",
    "ws2_32.dll",
    "netapi32.dll",
    "userenv.dll",
    "ntdll.dll",
    "shlwapi.dll",
    "setupapi.dll",
    "winmm.dll",
    "winspool.drv",
    "crypt32.dll",
    "bcrypt.dll",
    "secur32.dll",
    "iphlpapi.dll",
    "rpcrt4.dll",
    "msvcrt.dll",
    "version.dll",
    "uxtheme.dll",
    "dwmapi.dll",
    "mpr.dll",
    "netutils.dll",
    "wldap32.dll",
    "normaliz.dll",
    "psapi.dll",
    "imagehlp.dll",
    "dbghelp.dll",
    "cabinet.dll",
    "powrprof.dll",
    "propsys.dll",
    "dnsapi.dll",
    "nsi.dll",
    "sspicli.dll",
    "kernelbase.dll",
    "ucrtbase.dll",
    "msvcp140.dll",
    "msvcp140_1.dll",
    "concrt140.dll",
    "vcomp140.dll",
    "sechost.dll",
    "combase.dll",
    "msimg32.dll",
    "usp10.dll",
    "dwrite.dll",
    "gdiplus.dll",
    "oleacc.dll",
    "winhttp.dll",
    "wintrust.dll",
    "d3d11.dll",
    "dxgi.dll",
    "opengl32.dll",
    "glu32.dll",
    "wsock32.dll",
    "mswsock.dll",
    "cryptbase.dll",
    "msi.dll",
}


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: stage_tesseract.py EXTRACTED DEST")
    source = Path(sys.argv[1])
    dest = Path(sys.argv[2])
    exe = next(source.rglob("tesseract.exe"), None)
    trained = next(source.rglob("eng.traineddata"), None)
    if exe is None or trained is None:
        raise SystemExit("UB Mannheim extract is missing tesseract.exe or eng.traineddata")
    if trained.stat().st_size < 1_000_000:
        raise SystemExit(f"eng.traineddata is only {trained.stat().st_size} bytes")
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    (dest / "tessdata").mkdir()
    shutil.copy2(exe, dest / "tesseract.exe")
    present = {path.name.casefold(): path for path in exe.parent.iterdir() if path.is_file()}
    for name in _closure(exe, present):
        if name.casefold() == "tesseract.exe":
            continue
        shutil.copy2(present[name.casefold()], dest / name)
    shutil.copy2(trained, dest / "tessdata" / "eng.traineddata")
    for extra in ("eng.user-words", "eng.user-patterns"):
        found = next(source.rglob(extra), None)
        if found is not None:
            shutil.copy2(found, dest / "tessdata" / extra)
    for path in dest.iterdir():
        if path.suffix.casefold() in {".dll", ".exe"}:
            _strip_debug(path)
    staged = dest / "tessdata" / "eng.traineddata"
    print(f"staged {staged} ({staged.stat().st_size} bytes)")


def _closure(exe: Path, present: dict[str, Path]) -> set[str]:
    needed = {exe.name}
    queue = [exe.name]
    seen: set[str] = set()
    while queue:
        name = queue.pop()
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        path = present.get(key)
        if path is None:
            raise SystemExit(f"Tesseract import closure is missing {name}")
        for dep in _imports(path):
            dep_key = dep.casefold()
            if dep_key.startswith("api-ms-win-") or dep_key in SYSTEM:
                continue
            if dep_key not in present:
                raise SystemExit(f"{name} imports {dep}, which was not extracted")
            if dep_key not in seen:
                queue.append(dep)
                needed.add(dep)
    return needed


def _imports(path: Path) -> list[str]:
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


def _strip_debug(path: Path) -> None:
    data = bytearray(path.read_bytes())
    if data[:2] != b"MZ":
        return
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew : e_lfanew + 4] != b"PE\0\0":
        return
    coff = e_lfanew + 4
    _machine, nsec, _timestamp, symptr, nsym, optsize, _characteristics = struct.unpack_from(
        "<HHIIIHH", data, coff
    )
    opt = coff + 20
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic == 0x20B:
        dd_off = opt + 112
        section_align = struct.unpack_from("<I", data, opt + 32)[0]
    elif magic == 0x10B:
        dd_off = opt + 96
        section_align = struct.unpack_from("<I", data, opt + 32)[0]
    else:
        return
    num_dd = struct.unpack_from("<I", data, dd_off - 4)[0]
    sec_off = opt + optsize
    strtab = symptr + nsym * 18 if symptr and nsym and symptr + nsym * 18 < len(data) else 0

    def section_name(off: int) -> str:
        raw = bytes(data[off : off + 8])
        if raw.startswith(b"/") and strtab:
            try:
                index = int(raw[1:].split(b"\0", 1)[0])
            except ValueError:
                return raw.split(b"\0", 1)[0].decode("ascii", "replace")
            if strtab + index < len(data):
                end = data.index(b"\0", strtab + index)
                return bytes(data[strtab + index : end]).decode("ascii", "replace")
        return raw.split(b"\0", 1)[0].decode("ascii", "replace")

    headers = [(section_name(sec_off + index * 40), bytes(data[sec_off + index * 40 : sec_off + index * 40 + 40])) for index in range(nsec)]
    kept = [item for item in headers if not item[0].startswith(".debug")]
    if len(kept) == len(headers):
        return
    for index, (_name, blob) in enumerate(kept):
        data[sec_off + index * 40 : sec_off + index * 40 + 40] = blob
    for index in range(len(kept), nsec):
        data[sec_off + index * 40 : sec_off + index * 40 + 40] = b"\0" * 40
    struct.pack_into("<H", data, coff + 2, len(kept))
    struct.pack_into("<II", data, coff + 8, 0, 0)
    struct.pack_into("<I", data, opt + 64, 0)
    if num_dd > 6:
        struct.pack_into("<II", data, dd_off + 6 * 8, 0, 0)
    last = kept[-1][1]
    vsize, va, rsize, _raw = struct.unpack_from("<IIII", last, 8)
    end_va = va + max(vsize, rsize)
    align = section_align or 0x1000
    size_image = (end_va + align - 1) & ~(align - 1)
    struct.pack_into("<I", data, opt + 56, size_image)
    raw_end = sec_off + len(kept) * 40
    for _name, blob in kept:
        _vsize, _va, raw_size, raw_ptr = struct.unpack_from("<IIII", blob, 8)
        raw_end = max(raw_end, raw_ptr + raw_size)
    del data[raw_end:]
    path.write_bytes(data)


if __name__ == "__main__":
    main()
