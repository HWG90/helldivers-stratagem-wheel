"""Turn planned key names into ordinary pynput keypresses."""

from __future__ import annotations

from pynput.keyboard import Controller, Key, KeyCode

from stratagems.sequence import KeyController


class KeyboardSender(KeyController):
    """Sends input through the operating system. It does not attach to a process."""

    def __init__(self) -> None:
        self._keyboard = Controller()

    def press(self, key: str) -> None:
        self._keyboard.press(_to_key(key))

    def release(self, key: str) -> None:
        self._keyboard.release(_to_key(key))


def _to_key(name: str) -> Key | KeyCode:
    key_name = name.lower()
    if len(key_name) == 1:
        return KeyCode.from_char(key_name)
    aliases = {
        "ctrl_l": ("ctrl_l", "ctrl"),
        "ctrl": ("ctrl_l", "ctrl"),
        "shift_l": ("shift_l", "shift"),
        "shift": ("shift_l", "shift"),
        "alt_l": ("alt_l", "alt"),
        "alt": ("alt_l", "alt"),
    }
    for candidate in aliases.get(key_name, (key_name,)):
        key = getattr(Key, candidate, None)
        if key is not None:
            return key
    raise KeyError(name)
