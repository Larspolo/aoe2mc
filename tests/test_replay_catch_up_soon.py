"""Live replay on Paper: a unit behind its replay position closes the lag in the first CLOSE ms of its leg, not at
the end of a long leg (#1291: two villagers of de-64.3 stayed 4 to 10 blocks behind for 30 s). Fake RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import ai  # noqa: E402
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_catch_up import Entity  # noqa: E402
from test_replay_walk import VIL  # noqa: E402


def leg(at, d, reach):
    r = replay.Replay(Entity(at=at), data([]), ai=True)
    r.grid()                                                       # r.gather
    v = type("V", (), {"uuid": "u1", "pos": (60.5, 70.0, 10.5)})()
    return r.catch_up(v, d, reach)


def test_the_lag_closes_in_the_reach_of_a_long_leg():
    assert leg((10.5, 10.5), 45.0, 16.0) == pytest.approx(1 + 5 / 16)   # 5 blocks behind on a leg of 45 blocks
    assert leg((10.5, 10.5), 45.0, None) == pytest.approx(50 / 45)       # the whole leg: as before (#1168)
    assert leg((10.5, 10.5), 12.0, 16.0) == replay.CATCH_UP             # a short leg: its own length, capped
    assert leg((20.5, 10.5), 45.0, 16.0) == 1.0                         # ahead: never slower


def test_a_villager_10_blocks_behind_on_a_long_leg_walks_faster_than_before():
    """The case of #1291: 10 blocks behind on a leg of 49 blocks. Before, the factor was 59 / 49 (the lag closed at
    the end of the leg); now the lag closes in the first CLOSE ms (16 blocks of a villager), up to CATCH_UP."""
    speed = replay.SPEEDS["VILLAGER"] * 4                              # blocks per game second, tile size 4
    f = leg((60.5, 69.5), 49.0, speed * replay.CLOSE / 1000)
    assert f > 59 / 49 and min(replay.CATCH_UP, replay.PATH * f) == replay.CATCH_UP


def test_the_next_order_of_a_unit_behind_has_the_faster_speed():
    tl = [dict(time=1000, player=1, kind="move", objects=[7], tile=[12.5, 10.5]),
          dict(time=14000, player=1, kind="move", objects=[7], tile=[22.5, 10.5])]
    d = data(tl, n=128)
    d["objects"] += [VIL]
    now, game = [0.0], Entity(at=(46.5, 42.5))                      # 4 blocks before the end of the first walk
    r = replay.Replay(game, d, ai=True)
    r.run(4.0, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), log=None, finish=True)
    speeds = [c for c in game.sent if c.startswith("attribute u1 ")]
    f = 1 + 4 / (replay.SPEEDS["VILLAGER"] * 4 * replay.CLOSE / 1000)   # 4 blocks of lag in the first 16 blocks
    assert speeds[1] == ai.speed_command("u1", "VILLAGER_MALE", 4, 4.0 * min(replay.CATCH_UP, replay.PATH * f))
