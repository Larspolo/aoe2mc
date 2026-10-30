"""#2867 (epic #2538): a trigger with the condition "Object Has Action" fires in the scenario mode of the game program.
The tick function tests the score #r<ref> of aoe_action; scenario.actions sets it to the AoE2 UnitAIAction of the
state of the villager."""
import os
import sys
import types

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import scenario  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402

import aoe2mc  # noqa: E402

GATHER, IDLE, ATTACK = 10, 24, 1                                       # AoE2 UnitAIAction


def trig(action=GATHER, ref=7, inverted=False, next=-1):
    c = dict(type=aoe2mc.OBJECT_HAS_ACTION, timer=0, inverted=inverted, ref=ref, next=next, action=action)
    return dict(id=4, name="t", enabled=True, looping=False, conditions=[c],
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Busy", player=1, time=0, object=None, tile=[-1, -1],
                              area=[-1] * 4)])


def tick(t):
    load, out = aoe2mc.trigger_files([t], 4, np.full((16, 16), 64, np.int16))
    return load, out.get("data/aoe2mc/function/tick.mcfunction", "")


def test_the_tick_function_tests_the_action_score_of_the_unit():
    load, text = tick(trig())
    assert "execute if score #r7 aoe_action matches 10 unless score #4 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/4" in text
    assert "scoreboard objectives add aoe_action dummy" in load
    assert aoe2mc.action_list([trig()]) == [7]


def test_inverted_fires_when_the_unit_does_not_do_the_action():
    assert "execute unless score #r7 aoe_action matches 10 unless score #4 aoe_trig matches 1 run " in \
        tick(trig(inverted=True))[1]


def test_an_action_or_a_target_that_the_game_program_does_not_have_writes_no_trigger():
    for t in (trig(action=ATTACK), trig(ref=-1), trig(next=3)):
        assert tick(t)[1] == ""
        assert aoe2mc.action_list([t]) == []


def test_the_values_of_the_game_program_are_the_values_of_the_converter():
    assert sorted(set(scenario.ACTIONS.values())) == sorted(aoe2mc.OBJECT_ACTIONS)
    assert set(scenario.ACTIONS) == set(gather.EVENTS) | {"garrison"}    # each villager state has its action


def game():
    """Player 1 with a villager (ref 7) and a militia (ref 8); player 2 (a bot) with a villager (ref 9)."""
    objects = [dict(kind="unit", name="VILLAGER_MALE", player=1, uuid="v7", ref=7, tile=[2, 2]),
               dict(kind="unit", name="MILITIA", player=1, uuid="m8", ref=8, tile=[3, 3]),
               dict(kind="unit", name="VILLAGER_MALE", player=2, uuid="v9", ref=9, tile=[9, 9])]
    server = FakeServer({})
    data = grid([[64] * 12 for _ in range(12)], objects)
    data["players"] = {"0": {}, "1": {}, "2": {}}
    data["actions"] = [7, 8, 9, 10]
    g = gather.Gather(server, data)
    bot = gather.Gather(server, data, player=2)
    g.villagers = {"v7": gather.Villager("v7", (2.5, 64, 2.5))}
    bot.villagers = {"v9": gather.Villager("v9", (9.5, 64, 9.5))}
    g.bots = [types.SimpleNamespace(g=bot)]
    return server, g


def scores(server):
    return {c.split()[3]: int(c.split()[5]) for c in server.log if " aoe_action " in c}


def test_a_villager_that_chops_a_tree_has_the_score_of_gather():
    server, g = game()
    g.villagers["v7"].state = "chop"
    scenario.actions(g)
    assert scores(server) == {"#r7": GATHER, "#r8": 0, "#r9": IDLE, "#r10": 0}   # a militia, no unit: no action


def test_a_change_sends_one_command_once_per_second():
    server, g = game()
    scenario.actions(g)
    n = len(server.log)
    g.villagers["v7"].state = "to_site"
    scenario.actions(g)
    assert len(server.log) == n                                        # in the same second
    g.action_at = 0.0
    scenario.actions(g)
    assert server.log[n:] == ["scoreboard players set #r7 aoe_action 3"]   # BUILD
