"""Live replay with --pov: a look at an enemy building that the view team never explored gives no line (#5370).
Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

ENEMY = (20, 32, 20, 32)      # player 2: blocks x 20..32, z 20..32 -> tiles 5..7
OWN = (40, 52, 20, 32)        # player 1: the view player's own building
TILE = (6, 7)                 # the tile where a look from (26, 40) northward hits ENEMY


class Server(Fake):
    joined = frozenset({"Steve"})

    def command(self, cmd):
        self.sent.append(cmd)
        return ""


def setup(explored):
    r = replay.Replay(Server(), data([]))
    r.grid()
    r.starts = [(9, 2, "BARRACKS", ENEMY), (10, 1, "HOUSE", OWN)]
    r.pov, r.explored = 1, explored
    return r


def look(r, x):
    y = r.map.y(x, 40)
    r.eye = lambda name: ((float(x), y + 1.62, 40.0), (0.0, 0.0, -1.0))   # north, at the wall of the building
    return [c for c in r.inspect(10000, clock=lambda: 0.0) if " actionbar " in c]


def test_an_enemy_building_on_an_unexplored_tile_sends_no_line():
    assert not look(setup({1: {(0, 0)}}), 26)


def test_an_enemy_building_on_an_explored_tile_sends_its_line():
    (c,) = look(setup({1: {TILE}}), 26)
    assert c.startswith("title Steve actionbar ")
    assert replay.pretty("BARRACKS") in c


def test_an_enemy_building_seen_by_an_ally_sends_its_line():
    r = setup({2: {TILE}})
    r.data["players"]["1"]["team"] = 1
    r.data["players"]["2"]["team"] = 1
    assert len(look(r, 26)) == 1


def test_an_own_building_always_sends_its_line():
    assert len(look(setup({}), 46)) == 1


def test_without_a_view_player_an_unexplored_enemy_building_sends_its_line():
    r = setup({})
    r.pov = None
    assert len(look(r, 26)) == 1
