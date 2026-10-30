"""BACK TO WORK of the live replay (#1179): the units of a building come out and go back to the resource that they
left for the garrison, so a long jump counts their gather. Before, they stayed inside, and the jump to 43:30 of
samples/de-64.3 gave player 1 only 296 food (18 villagers in a town center at 41:17, back to work at 41:27). Fake RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_garrison import RECT, TC, TREE, order, play, vil  # noqa: E402


def back(t):
    return dict(time=t, player=1, kind="back_to_work", objects=[50], names=["TOWN_CENTER"])


@pytest.mark.parametrize("ai", [False, True])
def test_back_to_work_sends_them_to_their_tree(ai):
    tl = [order(0, [7], 20), order(20000, [7], 50, "garrison")]
    stay, _ = play(tl, 80000, ai, extra=[TREE])
    r, sent = play(tl + [back(40000)], 80000, ai, extra=[TREE])
    assert stay.garrisons == {RECT: [7]} and r.garrisons == {} and r.units[7].tree == (3, 12)
    assert "tag u1 remove aoe2mc.garrisoned" in sent and r.units[7].job == "fletcher"
    assert r.gathered[1]["wood"] > stay.gathered[1]["wood"] + 5


def test_a_jump_counts_the_wood_after_back_to_work():
    def wood(timeline):
        d = data(timeline)
        d["objects"] += [TC, vil(7, "u1", [2.5, 10.5]), TREE]
        r = replay.Replay(Fake(), d)
        r.jump(d["timeline"], 600000)
        return r.gathered.get(1, {}).get("wood", 0), r.garrisons
    stay, held = wood([order(0, [7], 20), order(20000, [7], 50, "garrison")])
    work, out = wood([order(0, [7], 20), order(20000, [7], 50, "garrison"), back(30000)])
    assert held == {RECT: [7]} and out == {}
    assert work > stay + 100                                           # about 0.39 wood per second for 570 s
