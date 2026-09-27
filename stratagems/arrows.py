"""Parse stratagem arrow glyphs out of a line of OCR text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal["up", "down", "left", "right"]

GLYPHS: dict[str, str] = {
    "up": "↑",
    "down": "↓",
    "left": "←",
    "right": "→",
}

MIN_ARROWS = 2
MAX_ARROWS = 12

_ARROW_CHAR: dict[str, Direction] = {
    "↑": "up",
    "↓": "down",
    "←": "left",
    "→": "right",
    "▲": "up",
    "▼": "down",
    "◄": "left",
    "►": "right",
    "⬆": "up",
    "⬇": "down",
    "⬅": "left",
    "➡": "right",
    "⇧": "up",
    "⇩": "down",
    "⇦": "left",
    "⇨": "right",
}

_WORD: dict[str, Direction] = {
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
}

_LETTER: dict[str, Direction] = {
    "u": "up",
    "d": "down",
    "l": "left",
    "r": "right",
}

_ASCII: dict[str, Direction] = {
    "^": "up",
    "v": "down",
    "V": "down",
    "<": "left",
    ">": "right",
}

_PUNCT = ".,;:|()[]{}'\"`"


@dataclass(frozen=True)
class Token:
    kind: Literal["word", "arrow"]
    value: str


def format_code(code: tuple[str, ...] | list[str]) -> str:
    return " ".join(GLYPHS[direction] for direction in code)


def parse_arrow_glyphs(text: str) -> list[str] | None:
    """Return a clean direction list, or None when the line is not a code.

    A clean parse is one contiguous run of 2–12 arrow tokens. Name words may
    sit before or after that run. A word sandwiched between arrows rejects
    the line so a half-read code is not treated as authoritative.
    """
    return _contiguous([token for token in tokenize(text)])


def split_name_and_arrows(text: str) -> tuple[str, list[str] | None]:
    tokens = tokenize(text)
    arrows = _contiguous(tokens)
    if arrows is None:
        return (" ".join(text.split()), None)
    words = [token.value for token in tokens if token.kind == "word"]
    return (" ".join(words).strip(), arrows)


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    buf: list[str] = []

    def flush() -> None:
        if not buf:
            return
        raw = "".join(buf)
        buf.clear()
        for piece in raw.split():
            tokens.extend(_classify_word(piece))

    for char in text:
        if char in _ARROW_CHAR:
            flush()
            tokens.append(Token("arrow", _ARROW_CHAR[char]))
            continue
        buf.append(char)
    flush()
    return tokens


def merge_orphan_arrow_lines(lines: list[str]) -> list[str]:
    """Attach a following arrow-only line to the name above it."""
    merged: list[str] = []
    for raw in lines:
        line = " ".join(raw.split())
        if not line:
            continue
        name, arrows = split_name_and_arrows(line)
        if arrows and not name and merged:
            merged[-1] = f"{merged[-1]} {line}"
        else:
            merged.append(line)
    return merged


def _classify_word(piece: str) -> list[Token]:
    core = piece.strip(_PUNCT)
    if not core:
        return []
    if all(char in _ASCII for char in core):
        return [Token("arrow", _ASCII[char]) for char in core]
    folded = core.casefold()
    if folded in _WORD:
        return [Token("arrow", _WORD[folded])]
    if len(folded) == 1 and folded in _LETTER:
        return [Token("arrow", _LETTER[folded])]
    if len(folded) >= MIN_ARROWS and all(char in _LETTER for char in folded):
        return [Token("arrow", _LETTER[char]) for char in folded]
    return [Token("word", core)]


def _contiguous(tokens: list[Token]) -> list[str] | None:
    indexes = [index for index, token in enumerate(tokens) if token.kind == "arrow"]
    if not indexes:
        return None
    if indexes[-1] - indexes[0] + 1 != len(indexes):
        return None
    directions = [tokens[index].value for index in indexes]
    if not MIN_ARROWS <= len(directions) <= MAX_ARROWS:
        return None
    return directions
