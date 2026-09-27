"""Package EquippedStratagems the way Bingus Shared Loader expects.

The archive layout matches the loader's public addon contract: a plaintext
HD2-Addon entry, seed-zero MurmurHash64A resource name, and a manager ZIP
whose root is manifest.json plus an Addon patch triple.
"""

from __future__ import annotations

import json
import re
import struct
import uuid
import zipfile
from pathlib import Path

ARCHIVE = "9ba626afa44a3aa3.patch_0"
TYPE = 0xA14E8DFA2CD117E2
RESOURCE = "mods/EquippedStratagems/EquippedStratagems"
GUID = "7f3a9c2e-6b14-4d58-8e21-0c5b9a4d71f6"
DISPLAY_NAME = "EquippedStratagems"
ROOT = Path(__file__).resolve().parent
ENTRY = ROOT / "EquippedStratagems.lua"
INSTALL = ROOT / "INSTALL.txt"
OUTPUT = ROOT / "EquippedStratagems.zip"


def resource_hash(name: str) -> int:
    data = name.encode("utf-8")
    mask, mix = (1 << 64) - 1, 0xC6A4A7935BD1E995
    value = len(data) * mix & mask
    end = len(data) // 8 * 8
    for (word,) in struct.iter_unpack("<Q", data[:end]):
        word = word * mix & mask
        word ^= word >> 47
        value = (value ^ (word * mix & mask)) * mix & mask
    if data[end:]:
        value = (value ^ int.from_bytes(data[end:], "little")) * mix & mask
    value ^= value >> 47
    value = value * mix & mask
    return value ^ (value >> 47)


def make_archive(resources: dict[int, bytes]) -> bytes:
    count = len(resources)
    offset = (104 + 80 * count + 15) & ~15
    entries = bytearray()
    body = bytearray(offset)
    for index, (name, resource) in enumerate(sorted(resources.items())):
        entries += struct.pack(
            "<7Q6I",
            name,
            TYPE,
            offset,
            0,
            0,
            0,
            0,
            len(resource),
            0,
            0,
            16,
            16,
            index,
        )
        body += resource
        body += b"\0" * (-len(body) % 16)
        offset = len(body)
    header = struct.pack("<III20sQQ24s", 0xF0000011, 1, count, b"", offset, 0, b"")
    types = struct.pack("<IIQIIII", 0, 0, TYPE, count, 0, 16, 16)
    body[: 104 + len(entries)] = header + types + entries
    return bytes(body)


def entry_source(source: bytes) -> bytes:
    if not re.fullmatch(r"mods/[A-Za-z0-9_]+/[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*", RESOURCE):
        raise ValueError("Use mods/<author>/<entry> with letters, digits and underscores")
    marker = f"-- HD2-Addon: {RESOURCE}\n".encode("utf-8")
    if len(marker) > 256:
        raise ValueError("Entry declaration must fit within 256 bytes including newline")
    if source.startswith(b"\xef\xbb\xbf") or b"\0" in source:
        raise ValueError("Entry must be plaintext UTF-8 without a BOM")
    source.decode("utf-8")
    if not source.startswith(marker):
        raise ValueError("Declaration must match the resource name")
    return source


def build(output: Path = OUTPUT) -> Path:
    body = entry_source(ENTRY.read_bytes())
    resource = struct.pack("<II", len(body), 2) + body
    archive = make_archive({resource_hash(RESOURCE): resource})
    description = (
        "Requires Bingus Shared Loader v15 or newer / API 1. "
        "Revision 9: exports selected and available mission stratagems, with native HUD eligibility for Hellbomb. "
        "Live mission updates include cooldown and objective eligibility filtering."
    )
    manifest = {
        "Version": 1,
        "Guid": str(uuid.UUID(GUID)),
        "Name": DISPLAY_NAME,
        "Description": description,
        "Options": [{"Name": DISPLAY_NAME, "Description": description, "Include": ["Addon"]}],
    }
    files = {
        "manifest.json": (json.dumps(manifest, indent=2) + "\n").encode(),
        "INSTALL.txt": INSTALL.read_bytes(),
        "Addon/" + ARCHIVE: archive,
        "Addon/" + ARCHIVE + ".stream": b"",
        "Addon/" + ARCHIVE + ".gpu_resources": b"",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for path, content in sorted(files.items()):
            info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            package.writestr(info, content)
    return output


if __name__ == "__main__":
    print(build())
