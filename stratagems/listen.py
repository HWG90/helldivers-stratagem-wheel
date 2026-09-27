"""Global mouse and keyboard listener for binds. Events are not swallowed."""

from __future__ import annotations

from collections.abc import Callable

from pynput.keyboard import Key, KeyCode
from pynput.keyboard import Listener as KeyboardListener
from pynput.mouse import Button
from pynput.mouse import Listener as MouseListener

from stratagems.binds import canonical_key_name

MouseHandler = Callable[[str, bool, int, int], None]
KeyHandler = Callable[[str, bool], None]
MoveHandler = Callable[[int, int], None]


def mouse_button_name(button: Button) -> str | None:
    found = _MOUSE_NAMES.get(button)
    return found


class InputListener:
    def __init__(
        self,
        on_mouse: MouseHandler,
        on_key: KeyHandler,
        on_move: MoveHandler | None = None,
    ) -> None:
        self._on_mouse = on_mouse
        self._on_key = on_key
        self._on_move = on_move
        self.pointer = (0, 0)
        self._held: set[str] = set()
        self._mouse: MouseListener | None = None
        self._keys: KeyboardListener | None = None

    def start(self) -> None:
        self._mouse = MouseListener(on_click=self._click, on_move=self._move)
        self._keys = KeyboardListener(on_press=self._press, on_release=self._release)
        self._mouse.start()
        self._keys.start()

    def stop(self) -> None:
        if self._mouse is not None:
            self._mouse.stop()
        if self._keys is not None:
            self._keys.stop()

    def _move(self, x: int, y: int) -> None:
        point = (int(x), int(y))
        self.pointer = point
        if self._on_move is not None:
            self._on_move(point[0], point[1])

    def _click(self, x: int, y: int, button: Button, pressed: bool) -> None:
        self.pointer = (int(x), int(y))
        name = mouse_button_name(button)
        if name is None:
            return
        self._on_mouse(name, pressed, int(x), int(y))

    def _press(self, key: Key | KeyCode) -> None:
        name = _key_name(key)
        if name is None or name in self._held:
            return
        self._held.add(name)
        self._on_key(name, True)

    def _release(self, key: Key | KeyCode) -> None:
        name = _key_name(key)
        if name is None:
            return
        self._held.discard(name)
        self._on_key(name, False)


def _key_name(key: Key | KeyCode) -> str | None:
    if isinstance(key, KeyCode):
        char = key.char
        if char and char.isprintable() and len(char) == 1:
            return canonical_key_name(char)
        return None
    if isinstance(key, Key):
        raw = key.name or ""
        if not raw:
            return None
        return canonical_key_name(raw)
    return None


def _mouse_names() -> dict[Button, str]:
    pairs = (
        ("left", "mouse1"),
        ("right", "mouse2"),
        ("middle", "mouse3"),
        ("x1", "mouse4"),
        ("x2", "mouse5"),
        ("button8", "mouse4"),
        ("button9", "mouse5"),
    )
    names: dict[Button, str] = {}
    for attr, label in pairs:
        button = getattr(Button, attr, None)
        if isinstance(button, Button):
            names[button] = label
    return names


_MOUSE_NAMES = _mouse_names()
