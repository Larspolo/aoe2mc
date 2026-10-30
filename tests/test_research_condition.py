"""#2656 (epic #2538): a trigger with the condition "Research Technology" fires in the scenario mode. The game program
sets the score #p<N>.<technology> of aoe_tech when player N researches a technology, and the tick function of the
datapack tests it."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import train  # noqa: E402
from test_scenario_mode import game  # noqa: E402

import aoe2mc  # noqa: E402


def trig(player=1, tech="LOOM", looping=False):
    return dict(id=7, name="t", enabled=True, looping=looping,
                conditions=[dict(type=aoe2mc.RESEARCHED, timer=0, inverted=False, player=player, technology=tech)],
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Loom!", player=1, time=0, object=None, tile=[-1, -1],
                              area=[-1] * 4)])


def test_the_condition_tests_the_score_of_the_technology_in_the_tick_function():
    load, files = aoe2mc.trigger_files([trig()])
    assert "execute if score #p1.LOOM aoe_tech matches 1.. unless score #7 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/7" in files["data/aoe2mc/function/tick.mcfunction"].splitlines()
    assert "scoreboard objectives add aoe_tech dummy" in load
    assert files["data/aoe2mc/function/trigger/7.mcfunction"].splitlines()[-1] == "scoreboard players set #7 aoe_trig 1"


def test_gaia_or_no_technology_gives_no_trigger():
    for t in (trig(player=0), trig(tech="")):
        assert aoe2mc.trigger_files([t])[1] == {}


def test_a_technology_of_the_scenario_mode_sets_its_score():
    server, g, bot = game({"0": {}, "1": {}, "2": {}})
    train.research(g, {"name": "LOOM", "player": "@a"})
    assert "scoreboard players set #p1.LOOM aoe_tech 1" not in server.log            # not in the other modes
    g.mode = "scenario"
    bot.modes = frozenset({"scenario"})
    train.research(g, {"name": "WHEELBARROW", "player": "@a"})
    train.research(bot, {"name": "LOOM", "player": "@a"})
    assert "scoreboard players set #p1.WHEELBARROW aoe_tech 1" in server.log
    assert "scoreboard players set #p2.LOOM aoe_tech 1" in server.log               # a bot too
