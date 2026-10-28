"""A saved game keeps the state of the victory modes (#2476, epic #2253): the defeated players, the players that the
conquest check saw, the Sudden Death towns, the King of the Hill timer and its drawn monument, the Battle Royale
Corruption time."""
import json

import pytest
from test_king_of_the_hill import run, setup

from game import hill, savegame, wonder


def loaded(g, *units, monument=True):
    server, h = setup(*units, monument=monument)
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return server, h


def test_a_loaded_game_has_the_defeated_players_towns_and_hill_timer():
    server, g = setup(("a", 1, 18.5, 16.5))
    run(g, 100 * wonder.YEAR)
    g.defeated, g.conquest_seen, g.towns = {3}, {1, 2, 3}, {1, 2}
    g.corruption_time, g.corruption_at = 120.0, 150.0
    server, h = loaded(g, ("a", 1, 18.5, 16.5))
    assert (h.defeated, h.conquest_seen, h.towns) == ({3}, {1, 2, 3}, {1, 2})
    assert h.hill == g.hill and h.hill["owner"] == 1
    assert (h.corruption_time, h.corruption_at) == (120.0, 150.0)
    left = h.hill["left"]
    run(h, 10)
    assert h.hill["owner"] == 1 and h.hill["left"] == pytest.approx(left - 10)   # it counts on from the saved time


def test_a_loaded_game_draws_no_second_monument():
    server, g = setup(("a", 1, 2.5, 2.5), monument=False)
    hill.tick(g, 1.0)                                                  # draws the monument in the center
    server, h = loaded(g, monument=False)
    n = len(server.log)
    hill.tick(h, 1.0)
    assert not any(c.startswith(("fill ", "setblock ")) for c in server.log[n:])
    assert h.monument == g.monument and (16, 16) in h.map.blocked
    assert hill.center(h) == hill.center(g)


def test_a_save_before_the_victory_modes_loads():
    server, g = setup()
    d = json.loads(json.dumps(savegame.dump(g), sort_keys=True))
    assert not set(savegame.VICTORY) & set(d["players"]["1"])
    _, h = setup()
    savegame.load(h, d)
    assert not set(savegame.VICTORY) & set(vars(h))
