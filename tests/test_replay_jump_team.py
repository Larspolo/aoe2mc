"""The gathered resources of the team game after a jump (#1229): player 4 of samples/de-63.0 had almost nothing. Three
causes: an ORDER on a hunt animal gave no food, the builders of a lumber camp or mining camp did not gather next to it,
and an ORDER on an own building put the villagers inside for good (later orders skipped them). Fake clock and RCON."""
import contextlib
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gather  # noqa: E402
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_garrison import RECT, play  # noqa: E402
from test_replay_garrison import order as orders  # noqa: E402
from test_replay_gather import TREE, VIL, order  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
END = 300000
SHEEP = {"kind": "unit", "name": "SHEEP", "player": 0, "uuid": "s1", "ref": 30, "tile": [5.5, 10.5]}
CAMP = dict(time=0, player=1, kind="build", type=562, name="LUMBER_CAMP", tile=[9.0, 10.0], objects=[7],
            names=["VILLAGER_MALE"])


def run(timeline, objects, ai=False, to=END):
    """Play to END with a jump to `to`. With the plugin a unit that works when the jump ends catches up in steps(),
    at most its one resource: the tests count only without the plugin."""
    d = data(timeline + [dict(time=END + 1000, player=1, kind="chat", text="end")])
    d["objects"] += [VIL, *objects]
    game = Clock()
    r = replay.Replay(game, d, ai=ai)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, to=to)
    return r


@pytest.mark.parametrize("ai", [False, True])
def test_a_hunt_counts_its_food_in_a_jump(ai):
    r = run([dict(order(0, 30), tile=[5.5, 10.5])], [SHEEP], ai)
    assert r.hunted == {30: (5, 10)} and (5, 10) in r.map.herds and r.units[7].tree == (5, 10)
    assert ai or r.gathered[1]["food"] >= gather.AOE2_WORK["hunt"] * (END - 30000) / 1000


def test_a_hunter_gathers_the_carcass_in_play():
    r = run([dict(order(0, 30), tile=[5.5, 10.5])], [SHEEP], to=None)
    assert r.gathered[1]["food"] == gather.HUNT_FOOD["SHEEP"] and r.map.carcasses[(5, 10)] == 0


@pytest.mark.parametrize("ai", [False, True])
def test_the_builder_of_a_lumber_camp_chops_next_to_it(ai):
    r = run([CAMP], [TREE], ai)
    assert r.units[7].tree == (5, 10)
    assert ai or r.gathered[1]["wood"] >= gather.AOE2_WORK["wood"] * (END - 30000 - 35000) / 1000   # the build, #1282


@pytest.mark.parametrize("ai", [False, True])
def test_an_order_takes_a_unit_out_of_its_building(ai):
    r, sent = play([orders(0, [7, 8], 50), orders(40000, [7], 20)], 80000, ai, extra=[TREE])
    assert r.garrisons == {RECT: [8]} and r.units[7].tree == (5, 10)
    assert "tag u1 remove aoe2mc.garrisoned" in sent and "tag u2 remove aoe2mc.garrisoned" not in sent


@pytest.mark.slow
def test_the_team_game_gathers_after_a_jump(tmp_path):
    """The jump to 22:00 of check #1192. Player 4 had 29 food and 27 wood. The food lower bounds come from the
    villagers and ages of the record. The rest of the wood of player 4 is the trained villagers that follow the
    gather point (#1227)."""
    import aoe2mc
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(os.path.join(ROOT, "samples", "de-63.0.aoe2record"), str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        d = json.load(f)
    to = 22 * 60000
    d["timeline"] = [e for e in d["timeline"] if e["time"] <= to + 1000]
    game = Clock()
    r = replay.Replay(game, d)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, to=to)
    got = {p: r.gathered.get(p, {}) for p in (1, 2, 3, 4)}
    assert got[4]["wood"] >= 1000, got
    for p, food in {1: 3200, 2: 3000, 3: 3000, 4: 3050}.items():
        assert got[p]["food"] >= food / 2, got
