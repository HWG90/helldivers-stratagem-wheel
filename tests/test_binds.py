from pynput.mouse import Button

from stratagems.listen import mouse_button_name


def test_mouse_buttons_use_the_documented_names() -> None:
    assert mouse_button_name(Button.middle) == "mouse3"
    side4 = getattr(Button, "x1", None)
    if side4 is None:
        side4 = getattr(Button, "button8")
    side5 = getattr(Button, "x2", None)
    if side5 is None:
        side5 = getattr(Button, "button9")
    assert mouse_button_name(side4) == "mouse4"
    assert mouse_button_name(side5) == "mouse5"
