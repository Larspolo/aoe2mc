"""Live replay: a villager gets the look of its AoE2 task (#868): one profession command when its work starts. Fake RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_gather import BUSH, MINE, TREE, VIL, order, play  # noqa: E402


def jobs(sent, uuid="u1"):
    return [c.split('"')[1].removeprefix("minecraft:") for c in sent if c.startswith(f"data merge entity {uuid} {{VillagerData")]


@pytest.mark.parametrize("ai", [False, True])
@pytest.mark.parametrize("target, job", [(TREE, "fletcher"), (BUSH, "farmer"), (MINE, "mason")])
def test_an_order_on_a_resource_gives_one_profession(target, job, ai):
    r, sent = play([order(0, target["ref"])], target, 30000, ai)
    assert jobs(sent) == [job] and r.units[7].job == job


def test_a_move_gives_no_profession():
    tl = [order(0, 20), dict(time=30000, player=1, kind="move", objects=[7], tile=[1.5, 1.5], names=["VILLAGER_MALE"])]
    r, sent = play(tl, TREE, 60000)
    assert jobs(sent) == ["fletcher", "nitwit"]


def test_the_end_of_the_wood_gives_no_profession():
    r, sent = play([order(0, 20)], TREE, 300000)
    assert r.map.trees[(5, 10)] == 0 and jobs(sent) == ["fletcher", "nitwit"]


def test_a_builder_and_a_farmer():
    farm = {"time": 0, "player": 1, "kind": "build", "type": 50, "name": "FARM", "tile": [10.0, 10.0], "objects": [7],
            "names": ["VILLAGER_MALE"]}
    house = dict(farm, type=70, name="HOUSE", tile=[3.0, 3.0], time=60000)
    r, sent = play([farm, house], [], 90000)
    assert jobs(sent) == ["mason", "farmer", "mason"]


def test_a_jump_sends_the_last_look():
    d = data([order(0, 20), order(5000, 21)])
    d["objects"] += [VIL, TREE, dict(BUSH, tile=[2.5, 4.5])]
    r = replay.Replay(Fake(), d)
    assert jobs(r.jump(d["timeline"], 10000)) == ["farmer"]
