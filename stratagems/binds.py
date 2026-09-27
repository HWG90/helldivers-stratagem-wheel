"""Human-readable names for stored binds."""

from __future__ import annotations

MOUSE_LABELS = {
    "mouse1": "Mouse1 (left)",
    "mouse2": "Mouse2 (right)",
    "mouse3": "Mouse3 (middle)",
    "mouse4": "Mouse4",
    "mouse5": "Mouse5",
}

KEY_LABELS = {
    "ctrl_l": "Left Control",
    "ctrl": "Left Control",
    "ctrl_r": "Right Control",
    "shift": "Shift",
    "shift_l": "Left Shift",
    "shift_r": "Right Shift",
    "alt": "Alt",
    "alt_l": "Left Alt",
    "alt_r": "Right Alt",
    "alt_gr": "Alt Gr",
    "space": "Space",
    "enter": "Enter",
    "tab": "Tab",
    "esc": "Escape",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "backspace": "Backspace",
    "caps_lock": "Caps Lock",
    "page_up": "Page Up",
    "page_down": "Page Down",
    "home": "Home",
    "end": "End",
    "insert": "Insert",
    "delete": "Delete",
    "w": "W",
    "a": "A",
    "s": "S",
    "d": "D",
}


def display_bind(name: str) -> str:
    key = name.lower()
    if key in MOUSE_LABELS:
        return MOUSE_LABELS[key]
    if key in KEY_LABELS:
        return KEY_LABELS[key]
    if len(key) == 1:
        return key.upper()
    return key.replace("_", " ").title()


def canonical_key_name(name: str) -> str:
    """Fold platform aliases so Left Control is always stored as ctrl_l."""
    key = name.lower()
    aliases = {"ctrl": "ctrl_l", "shift": "shift_l", "alt": "alt_l"}
    return aliases.get(key, key)
