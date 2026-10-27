"""game/monk.py: a unit with no position (the server does not find it) does not stop the heal pass and the game loop
(#1980: a KeyError in a game of two people)."""
import pytest
from test_monk_heal import run, setup


def test_a_unit_without_a_position_does_not_stop_the_heal():
    server, g = setup(("a", "MILITIA", 1, 8.5, 10.0, 40.0), ("gone", "MILITIA", 1, 7.5, 10.0, 40.0))
    del server.entities["gone"]                                        # "data get entity" finds no position
    run(g, 4)
    assert server.entities["a"]["Health"] == pytest.approx(10 + 4 * 2.5)
