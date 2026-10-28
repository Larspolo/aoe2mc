"""#2756 (epic #2538): triggers with the conditions "Object Visible" and "Object Not Visible" fire in the scenario mode of
the game program. The tick function tests the score #r<ref>.p<player> of aoe_seen; scenario.visible sets it from the
sight of the player (the fog of the game program)."""
import os
import sys
import types

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import aoe2mc  # noqa: E402
import gather  # noqa: E402
import scenario  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402


def trig(kind, ref=5, player=1):
    c = dict(type=kind, timer=0, inverted=False, ref=ref, player=player)
    return dict(id=4, name="t", enabled=True, looping=False, conditions=[c],
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Seen", player=1, time=0, object=None, tile=[-1, -1],
                              area=[-1] * 4)])


def files(*triggers):
    return aoe2mc.trigger_files(list(triggers), 4, np.full((16, 16), 64, np.int16))


def test_the_tick_function_tests_the_score_of_the_sight():
    load, out = files(trig(aoe2mc.OBJECT_VISIBLE_MULTIPLAYER, player=2))
    assert "execute if score #r5.p2 aoe_seen matches 1 unless score #4 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/4" in out["data/aoe2mc/function/tick.mcfunction"]
    assert "scoreboard objectives add aoe_seen dummy" in load
    assert aoe2mc.visible_list([trig(aoe2mc.OBJECT_VISIBLE_MULTIPLAYER, player=2)]) == [(5, 2)]


def test_object_not_visible_tests_a_score_of_0():
    tick = files(trig(aoe2mc.OBJECT_NOT_VISIBLE))[1]["data/aoe2mc/function/tick.mcfunction"]
    assert "execute if score #r5.p1 aoe_seen matches 0 " in tick
    assert "if score #r0.p1 aoe_seen matches 1 " in files(trig(aoe2mc.OBJECT_VISIBLE, ref=0))[1][
        "data/aoe2mc/function/tick.mcfunction"]                         # reference 0 is an object too


def test_a_condition_with_no_object_or_player_writes_no_trigger():
    for t in (trig(aoe2mc.OBJECT_VISIBLE, ref=-1), trig(aoe2mc.OBJECT_VISIBLE_MULTIPLAYER, player=0)):
        assert "data/aoe2mc/function/trigger/4.mcfunction" not in files(t)[1]
        assert aoe2mc.visible_list([t]) == []


def game(pos):
    """Player 1 with a militia at (2, 2), player 2 with a militia (ref 5) and a house (ref 6), on 30 x 30 tiles of 1
    block. pos: the feet positions that Gather.where answers."""
    objects = [dict(kind="unit", name="MILITIA", player=1, uuid="s1", tile=[2, 2]),
               dict(kind="unit", name="MILITIA", player=2, uuid="e5", ref=5, tile=[4, 4]),
               dict(kind="building", name="HOUSE", player=2, ref=6, footprint=[26, 26, 28, 28], tile=[26, 26])]
    server = FakeServer({u: {"Pos": p} for u, p in pos.items()})          # alive at the census (#3122)
    data = grid([[64] * 30 for _ in range(30)], objects)
    data["players"] = {"0": {}, "1": {}, "2": {}}
    g = gather.Gather(server, data).setup()
    bot = gather.Gather(server, data, player=2).setup()
    g.bots = [types.SimpleNamespace(g=bot)]
    g.where = lambda want: {u: p for u, p in pos.items() if u in want}
    return server, g


def scores(server):
    return {c.split()[3]: int(c.split()[5]) for c in server.log if c.endswith(tuple(" 01")) and " aoe_seen " in c}


def test_the_scenario_mode_sets_the_score_from_the_sight_of_the_player():
    server, g = game({"s1": (2.5, 64, 2.5), "e5": (4.5, 64, 4.5)})
    g.data["visible"] = [[5, 1], [6, 1], [6, 2], [5, 3]]
    scenario.visible(g)
    assert scores(server) == {"#r5.p1": 1, "#r6.p1": 0, "#r6.p2": 1, "#r5.p3": 0}   # player 3 is not in the game


def test_a_dead_or_far_unit_is_not_visible():
    server, g = game({"s1": (2.5, 64, 2.5), "e5": (25.5, 64, 2.5)})
    g.data["visible"] = [[5, 1]]
    scenario.visible(g)
    assert scores(server) == {"#r5.p1": 0}
    server, g = game({"s1": (2.5, 64, 2.5)})
    g.data["visible"] = [[5, 1]]
    scenario.visible(g)
    assert scores(server) == {"#r5.p1": 0}


def test_with_no_visible_conditions_the_scenario_mode_sends_nothing():
    server, g = game({"s1": (2.5, 64, 2.5)})
    scenario.visible(g)
    assert scores(server) == {}
