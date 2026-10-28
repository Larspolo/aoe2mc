"""#2678: an AUTOSCOUT of the record: the scout walks to the nearest tile that its player did not explore, then to the
next one, until another order. Fake RCON on Paper (the plugin walks the units)."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_replay_patrol import START, walks  # noqa: E402


def scout(t):
    return dict(time=t, player=1, kind="autoscout", objects=[8])


def test_the_scout_walks_to_unexplored_tiles_one_after_the_other():
    r, goals = walks([scout(0)], 60000)
    assert len(goals) >= 3 and len(set(goals)) == len(goals)       # a new tile at each arrival
    assert math.dist(goals[0], START) < 8 * 4                       # the nearest unexplored tile: near the scout
    assert 8 in r.scouts and {(int(x // 4), int(z // 4)) for x, _, z in goals} <= r.scouts[8]


def test_a_later_move_ends_the_scouting():
    r, goals = walks([scout(0), dict(time=30000, player=1, kind="move", objects=[8], names=["MILITIA"],
                                     tile=[3.5, 3.5])], 90000)
    assert goals[-1] == (14.5, 70.0, 14.5) and 8 not in r.scouts
    assert r.units[8].pos == (14.5, 70.0, 14.5)                  # it stays at the tile of the move


def test_the_scouting_ends_when_the_player_explored_all_tiles():
    r, goals = walks([scout(0)], 900000)
    assert 8 not in r.scouts and goals
