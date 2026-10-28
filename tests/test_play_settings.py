"""game/run.py: the AoE2 lobby settings go to play() through one table (run.SETTINGS, #2373), so that a new setting is
one new line there and not a change of the lines of play() that each setting changed (4 merge conflicts in one hour)."""
import inspect

import pytest

from game import run


def test_each_setting_has_an_option_of_the_same_name(capsys):
    with pytest.raises(SystemExit):
        run.main(["--help"])
    out = capsys.readouterr().out
    for k in run.SETTINGS:
        assert f"--{k.replace('_', '-')}" in out, k


def test_the_settings_are_in_alphabetical_order_and_not_in_the_signature():
    assert list(run.SETTINGS) == sorted(run.SETTINGS)
    assert not set(run.SETTINGS) & set(inspect.signature(run.play).parameters)


def test_an_unknown_setting_stops_play():
    with pytest.raises(TypeError, match="no setting colour"):
        run.play(None, "no-world", colour="red")
