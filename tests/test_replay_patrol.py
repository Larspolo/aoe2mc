"""#2550: a PATROL of the record: the unit walks between its place and the patrol tile, again and again, until another
order; a second PATROL adds a point (AoE2 shift patrol). Fake RCON on Paper (the plugin walks the units)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_ai import MIL, orders  # noqa: E402

START = (14.5, 70.0, 42.5)                                       # the cell of MIL (tile 3.5, 10.5)


def walks(timeline, end):
    """The goals of the walk orders of MILITIA u2, in order, until game time end (ms)."""
    d = data(timeline + [dict(time=end, player=1, kind="chat", text="end")])
    d["objects"] += [MIL]
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d, ai=True)
    r.run(4.0, clock=lambda: now[0], sleep=sleep, log=None)
    goals = [orders([c])["u2"] for c in game.sent if c.startswith("aoe moveto u2 ")]
    return r, [g for k, g in enumerate(goals) if not k or g != goals[k - 1]]   # the legs of one walk: one goal


def patrol(t, tile):
    return dict(time=t, player=1, kind="patrol", objects=[8], names=["MILITIA"], tile=tile)


def test_a_patrol_walks_to_the_tile_and_back_again_and_again():
    r, goals = walks([patrol(0, [10.5, 10.5])], 60000)
    assert goals[:4] == [(42.5, 70.0, 42.5), START, (42.5, 70.0, 42.5), START]
    assert 8 in r.patrols


def test_a_later_move_ends_the_patrol():
    r, goals = walks([patrol(0, [10.5, 10.5]), dict(time=30000, player=1, kind="move", objects=[8],
                                                    names=["MILITIA"], tile=[3.5, 3.5])], 90000)
    assert goals[-1] == (14.5, 70.0, 14.5) and 8 not in r.patrols
    assert r.units[8].pos == (14.5, 70.0, 14.5)                  # it stays at the tile of the move


def test_a_second_patrol_adds_a_point_to_the_route():
    r, goals = walks([patrol(0, [10.5, 10.5]), patrol(500, [10.5, 3.5])], 90000)
    assert goals[:4] == [(42.5, 70.0, 42.5), (42.5, 70.0, 14.5), (42.5, 70.0, 42.5), START]
    assert r.patrols[8][0] == [[3.5, 10.5], [10.5, 10.5], [10.5, 3.5]]


def test_a_patrol_to_its_own_place_ends():
    r, goals = walks([patrol(0, [3.5, 10.5])], 10000)              # no walk: no endless turns at one game time
    assert len(goals) <= 1 and not r.moving
