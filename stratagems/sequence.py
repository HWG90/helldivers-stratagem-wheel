"""Build and play the key sequence for one stratagem code."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Protocol, Sequence, assert_never

from stratagems.arrows import format_code
from stratagems.binds import display_bind

DirectionStyle = Literal["arrows", "wasd"]
Action = Literal["down", "up"]

_ARROW_KEYS = {"up": "up", "down": "down", "left": "left", "right": "right"}
_WASD_KEYS = {"up": "w", "down": "s", "left": "a", "right": "d"}


@dataclass(frozen=True)
class InputStep:
    t_ms: int
    action: Action
    key: str


class KeyController(Protocol):
    def press(self, key: str) -> None: ...

    def release(self, key: str) -> None: ...


def direction_to_key(direction: str, style: DirectionStyle) -> str:
    match style:
        case "arrows":
            table = _ARROW_KEYS
        case "wasd":
            table = _WASD_KEYS
        case unreachable:
            assert_never(unreachable)
    try:
        return table[direction]
    except KeyError as exc:
        raise ValueError(f"unknown direction: {direction}") from exc


def plan_input(
    directions: Sequence[str],
    *,
    modifier: str,
    style: DirectionStyle,
    start_delay_ms: int,
    gap_ms: int,
    tail_ms: int,
    tap_ms: int,
) -> list[InputStep]:
    """Hold the modifier, tap each direction, then release the modifier.

    ``start_delay_ms`` waits after the modifier goes down, before the first
    direction. ``gap_ms`` waits between releasing one direction and pressing
    the next. ``tail_ms`` waits after the last direction release before the
    modifier comes up. ``tap_ms`` is how long each direction key stays down.
    """
    for label, value in (
        ("start_delay_ms", start_delay_ms),
        ("gap_ms", gap_ms),
        ("tail_ms", tail_ms),
        ("tap_ms", tap_ms),
    ):
        if value < 0:
            raise ValueError(f"{label} must be >= 0")

    steps = [InputStep(0, "down", modifier)]
    if not directions:
        steps.append(InputStep(tail_ms, "up", modifier))
        return steps

    t = start_delay_ms
    last = len(directions) - 1
    for index, direction in enumerate(directions):
        key = direction_to_key(direction, style)
        steps.append(InputStep(t, "down", key))
        up_at = t + tap_ms
        steps.append(InputStep(up_at, "up", key))
        if index == last:
            t = up_at + tail_ms
        else:
            t = up_at + gap_ms
    steps.append(InputStep(t, "up", modifier))
    return steps


def format_plan(steps: Sequence[InputStep], *, name: str, code: Sequence[str]) -> str:
    lines = [name, format_code(tuple(code)), ""]
    for step in steps:
        lines.append(f"{step.t_ms:6d} ms  {display_bind(step.key):<16} {step.action}")
    return "\n".join(lines)


def execute_plan(
    steps: Sequence[InputStep],
    controller: KeyController,
    *,
    sleep: Callable[[float], None],
    now: Callable[[], float],
) -> None:
    """Play a plan. Keys that are still down are released if a step fails."""
    pressed: list[str] = []
    origin = now()
    try:
        for step in steps:
            delay = (origin + step.t_ms / 1000) - now()
            if delay > 0:
                sleep(delay)
            match step.action:
                case "down":
                    controller.press(step.key)
                    pressed.append(step.key)
                case "up":
                    controller.release(step.key)
                    _drop_one(pressed, step.key)
                case unreachable:
                    assert_never(unreachable)
    finally:
        for key in reversed(pressed):
            try:
                controller.release(key)
            except Exception:
                continue


def _drop_one(pressed: list[str], key: str) -> None:
    try:
        pressed.remove(key)
    except ValueError:
        return

