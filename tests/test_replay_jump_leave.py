"""A unit that leaves its building by an order in the skipped time of a jump of the live replay is out of it in
Minecraft too (#3023). Fake RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import Fake, data  # noqa: E402
from test_replay_garrison import RECT, TC, vil  # noqa: E402

import replay  # noqa: E402


def inside_replay(ai):
    d = data([{"time": 0, "player": 1, "kind": "order", "objects": [7, 8], "target": 50, "names": ["VILLAGER_MALE"] * 2}])
    d["objects"] += [TC, vil(7, "u1", [2.5, 10.5]), vil(8, "u2", [2.5, 11.5])]
    r = replay.Replay(Fake(), d, ai=ai)
    r.jump(d["timeline"], 30000)
    assert r.garrisons == {RECT: [7, 8]}
    return r


@pytest.mark.parametrize("ai", [False, True])
def test_a_move_in_the_skipped_time_takes_the_unit_out_for_good(ai):
    r = inside_replay(ai)
    move = {"time": 50000, "player": 1, "kind": "move", "objects": [7], "tile": [1.5, 1.5], "names": ["VILLAGER_MALE"]}
    sent = r.jump([move], 60000, 45000)
    assert r.garrisons == {RECT: [8]}
    assert "data merge entity u1 {Invulnerable:0b}" in sent and "tag u1 remove aoe2mc.garrisoned" in sent
    assert ("aoe label u1" in sent) == ai
    assert not any(c.startswith("data merge entity u2 {Invulnerable:0b}") for c in sent)   # u2 stays inside


@pytest.mark.parametrize("ai", [False, True])
def test_a_unit_that_stays_inside_gets_no_leave_command(ai):
    r = inside_replay(ai)
    sent = r.jump([], 60000, 45000)
    assert r.garrisons == {RECT: [7, 8]}
    assert not any("aoe2mc.garrisoned" in c and "remove" in c for c in sent)
    assert not any(c.startswith("data merge entity u") and "Invulnerable:0b" in c for c in sent)
