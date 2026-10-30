"""A long jump of the live replay counts the food of the villagers that built a farm and farm it, and a builder stops
its work at its old resource (#1222). Fake clock and RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gather  # noqa: E402
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_farm import VIL, farm_build, order  # noqa: E402
from test_replay_gather import TREE  # noqa: E402

END = 300000


def jump(timeline, ai):
    d = data(timeline + [dict(time=END + 1000, player=1, kind="chat", text="end")])
    d["objects"] += [VIL, TREE]
    game = Clock()
    r = replay.Replay(game, d, ai=ai)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, to=END)
    return r.gathered.get(1, {})


@pytest.mark.parametrize("ai", [False, True])
def test_the_builder_of_a_farm_farms_it_in_a_jump(ai):
    food = jump([farm_build(0)], ai).get("food", 0)
    assert food >= gather.AOE2_WORK["farm"] * (END - 30000 - 15000) / 1000     # less the walk, the build (#1282)


@pytest.mark.parametrize("ai", [False, True])
def test_a_builder_stops_chopping(ai):
    got = jump([order(0, 20, (5.5, 10.5)), farm_build(100000)], ai)
    assert gather.AOE2_WORK["wood"] * 80 <= got["wood"] <= gather.AOE2_WORK["wood"] * 100   # 0 to 100 s only
    assert got["food"] >= gather.AOE2_WORK["farm"] * (END - 130000 - 15000) / 1000
