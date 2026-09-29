"""The suite runs offscreen however it was started.

`tests/conftest.py` forces the platform; this is what notices if that line is
lost or moved below a Qt import, before a run puts every window on the desktop.
"""


def test_the_application_runs_on_the_offscreen_platform(qapp) -> None:
    assert qapp.platformName() == "offscreen"
