from stratagems.catalog import STRATAGEMS, get
from stratagems.sequence import execute_plan, plan_input


def test_two_direction_timing() -> None:
    steps = plan_input(
        ["up", "right"],
        modifier="ctrl_l",
        style="arrows",
        start_delay_ms=80,
        gap_ms=50,
        tail_ms=40,
        tap_ms=20,
    )
    assert [(step.t_ms, step.action, step.key) for step in steps] == [
        (0, "down", "ctrl_l"),
        (80, "down", "up"),
        (100, "up", "up"),
        (150, "down", "right"),
        (170, "up", "right"),
        (210, "up", "ctrl_l"),
    ]


def test_wasd_and_single_direction() -> None:
    steps = plan_input(
        ["down"],
        modifier="ctrl_l",
        style="wasd",
        start_delay_ms=80,
        gap_ms=50,
        tail_ms=40,
        tap_ms=20,
    )
    assert [(step.t_ms, step.action, step.key) for step in steps] == [
        (0, "down", "ctrl_l"),
        (80, "down", "s"),
        (100, "up", "s"),
        (140, "up", "ctrl_l"),
    ]


def test_negative_timing_is_rejected() -> None:
    try:
        plan_input(["up"], modifier="ctrl_l", style="arrows", start_delay_ms=-1, gap_ms=0, tail_ms=0, tap_ms=0)
    except ValueError as exc:
        assert "start_delay_ms" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_every_catalog_code_plans_in_order() -> None:
    for stratagem in STRATAGEMS:
        steps = plan_input(
            stratagem.code,
            modifier="ctrl_l",
            style="arrows",
            start_delay_ms=80,
            gap_ms=50,
            tail_ms=40,
            tap_ms=20,
        )
        assert steps[0] == steps[0].__class__(0, "down", "ctrl_l")
        assert steps[-1].action == "up"
        assert steps[-1].key == "ctrl_l"
        downs = [step.key for step in steps if step.action == "down" and step.key != "ctrl_l"]
        assert tuple(downs) == stratagem.code
        assert all(steps[index].t_ms <= steps[index + 1].t_ms for index in range(len(steps) - 1))


def test_reinforce_matches_published_code() -> None:
    reinforce = get("Reinforce")
    assert reinforce is not None
    assert reinforce.code == ("up", "down", "right", "left", "up")


class _Clock:
    def __init__(self) -> None:
        self.now_s = 0.0

    def now(self) -> float:
        return self.now_s

    def sleep(self, delay: float) -> None:
        self.now_s += delay


class _Keys:
    def __init__(self, fail_on: str | None = None) -> None:
        self.events: list[tuple[str, str]] = []
        self.fail_on = fail_on

    def press(self, key: str) -> None:
        if key == self.fail_on:
            raise RuntimeError("device rejected the key")
        self.events.append(("down", key))

    def release(self, key: str) -> None:
        self.events.append(("up", key))


def test_executor_plays_steps_on_a_virtual_clock() -> None:
    steps = plan_input(
        ["up", "right"],
        modifier="ctrl_l",
        style="arrows",
        start_delay_ms=80,
        gap_ms=50,
        tail_ms=40,
        tap_ms=20,
    )
    clock = _Clock()
    keys = _Keys()
    execute_plan(steps, keys, sleep=clock.sleep, now=clock.now)
    assert keys.events == [(step.action, step.key) for step in steps]
    assert clock.now_s == steps[-1].t_ms / 1000


def test_executor_releases_a_held_modifier_when_a_press_fails() -> None:
    steps = plan_input(
        ["up"],
        modifier="ctrl_l",
        style="arrows",
        start_delay_ms=0,
        gap_ms=0,
        tail_ms=0,
        tap_ms=0,
    )
    keys = _Keys(fail_on="up")
    try:
        execute_plan(steps, keys, sleep=lambda _delay: None, now=lambda: 0.0)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected the failed press to surface")
    assert ("down", "ctrl_l") in keys.events
    assert ("up", "ctrl_l") in keys.events
