"""Live replay: a trained unit walks to the GATHER POINT of its building, and a villager gathers there when the point is
on a resource, also in a jump (#1227). Fake clock and RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_spawn import TC, queue  # noqa: E402

import gather  # noqa: E402
import replay  # noqa: E402

TREE = {"kind": "other", "name": "TREE_OAK", "player": 0, "ref": 20, "tile": [10.5, 4.5]}
SPAWN = 26000                                                          # the villager of queue(): 1 s + 25 s


def point(t=500, target=20, tile=(10.5, 4.5)):
    return dict(time=t, player=1, kind="gather_point", objects=[5], tile=list(tile),
                **({} if target is None else {"target": target}))


def play(timeline, end, ai=False, to=None):
    d = data(timeline + [dict(time=end, player=1, kind="chat", text="end")])
    d["objects"] += [TC, TREE]
    game = Clock()
    r = replay.Replay(game, d, ai=ai)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, to=to)
    return r


@pytest.mark.parametrize("ai", [False, True])
def test_a_villager_of_a_town_center_with_a_gather_point_on_a_tree_chops_it(ai):
    r = play([point(), queue()], 120000, ai)
    v, = [v for i, v in r.units.items() if i < 0]
    assert r.map.trees[(10, 4)] < gather.TREE_WOOD and -1 in r.working and v.tree == (10, 4)


@pytest.mark.parametrize("ai", [False, True])
def test_a_jump_counts_the_wood_of_the_gather_point(ai):
    end = 200000                                                       # the tree has TREE_WOOD wood
    r = play([point(), queue()], end + 1000, ai, to=end)
    wood = r.gathered.get(1, {}).get("wood", 0)
    rate = gather.AOE2_WORK["wood"]
    assert rate * (end - SPAWN - 15000) / 1000 <= wood <= rate * (end - SPAWN) / 1000


def test_a_gather_point_on_the_ground_only_sends_the_unit_there():
    r = play([point(target=None, tile=(12.5, 12.5)), queue()], 120000)
    v = r.units[-1]
    assert v.tree is None and not r.working and v.cell == (50, 50)


def test_the_first_command_of_the_unit_takes_it_over_with_its_work():
    order = dict(time=100000, player=1, kind="order", objects=[300], target=20, names=["VILLAGER_MALE"])
    r = play([point(), queue(), order], 200000)
    assert r.adopted == {-1: 300} and not [i for i in r.units if i < 0] and 300 in r.working
    end = 300000
    r = play([point(), queue(), dict(order, kind="move", tile=[1.5, 14.5])], end + 1000, to=end)
    wood = r.gathered.get(1, {}).get("wood", 0)                       # it chops from its arrival to the MOVE
    assert gather.AOE2_WORK["wood"] * (100000 - SPAWN - 15000) / 1000 <= wood <= gather.AOE2_WORK["wood"] * 74


@pytest.mark.slow
def test_the_jump_to_43_30_of_the_sample_record_counts_the_food_of_the_gather_points(tmp_path):
    """Before #1227 the jump gave food 3092 (player 1) and 4115 (player 2), with the hunts of #1229 about 5500, with
    the fish of #1283 7353 and 7484. The lower bounds of the record (villagers, ages and the market) are 4650 and 6300."""
    import contextlib
    import io
    import json

    import aoe2mc
    pytest.importorskip("mgz.model")
    rec = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(rec, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        d = json.load(f)
    game = Clock()
    r = replay.Replay(game, d)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, to=(43 * 60 + 30) * 1000)
    food = {p: g.get("food", 0) for p, g in r.gathered.items()}
    assert food[1] >= 4650 and food[2] >= 6300, food
    assert len(r.adopted) > 50                                         # the record names many of them later
