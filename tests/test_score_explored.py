"""#2396: the AoE2 score gets 10 technology points for each 1 % of the explored map (game/score.py, explore)."""
import pytest
from test_score import two_sides

from game import combat, score  # noqa: F401 (combat puts game/ on sys.path)


def explore(g):
    g.explore_at = 0.0                                                 # no wait of LOOK seconds
    score.explore(g)


def test_a_unit_that_walks_to_new_tiles_raises_the_technology_points():
    server, g, bot = two_sides()
    assert score.tiles(g) == 20 * 20
    explore(g)
    seen = len(g.explored)
    assert (2, 2) in g.explored and (18, 18) not in g.explored
    assert score.points(g)[1]["technology"] == pytest.approx(10 * 100 * seen / 400)
    server.entities["v-1"]["Pos"] = (18.5, 64.0, 18.5)                 # the villager walks to the far corner
    explore(g)
    assert (18, 18) in g.explored and (2, 2) in g.explored and len(g.explored) > seen   # explored stays explored
    assert score.points(g)[1]["technology"] == pytest.approx(10 * 100 * len(g.explored) / 400)
    tech = score.points(g)[1]["technology"]
    server.entities["v-1"]["Pos"] = (2.5, 64.0, 2.5)                   # back on known tiles: no new points
    server.entities["m-1"]["Pos"] = (2.5, 64.0, 2.5)
    explore(g)
    assert score.points(g)[1]["technology"] == pytest.approx(tech)


def test_a_bot_gather_counts_its_own_explored_tiles():
    server, g, bot = two_sides()
    explore(g)                                                         # one call for all Gathers of the game
    assert (11, 11) in bot.explored and (2, 2) not in bot.explored     # the house of player 2 sees, not its rival
    assert (11, 11) not in g.explored
    assert score.points(g)[2]["technology"] == pytest.approx(10 * 100 * len(bot.explored) / 400)


def test_the_tiles_are_updated_at_most_each_look_seconds():
    server, g, bot = two_sides()
    explore(g)
    seen = set(g.explored)
    server.entities["v-1"]["Pos"] = (18.5, 64.0, 18.5)
    score.explore(g)                                                   # less than LOOK seconds later: no update
    assert g.explored == seen
