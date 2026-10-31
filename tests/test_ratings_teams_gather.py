"""ratings.teams reads the sides of the Game behind a Gather (g.game.sides, #5224): the server check found no change."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import ratings  # noqa: E402


def test_teams_of_a_gather_use_the_sides_of_its_game():
    g = SimpleNamespace(players={}, game=SimpleNamespace(sides={"Alpha": 1, "Beta": 2}))
    assert ratings.teams(g, 1) == [(["Alpha"], True), (["Beta"], False)]
