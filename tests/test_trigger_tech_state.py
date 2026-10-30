"""#2769 (epic #2538): triggers fire on the conditions "Researching Technology" and "Technology State" in the scenario
mode. The game program sets the score #p<N>.<technology> of aoe_techstate to the AoE2 TechnologyState, and the tick
function of the datapack tests it."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402

import aoe2mc  # noqa: E402

TICK = "data/aoe2mc/function/tick.mcfunction"


def trig(kind, player=1, tech="LOOM", **more):
    return dict(id=7, name="t", enabled=True, looping=False,
                conditions=[dict(type=kind, timer=0, inverted=False, player=player, technology=tech, **more)],
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Loom!", player=1, time=0, object=None, tile=[-1, -1],
                              area=[-1] * 4)])


def test_researching_technology_tests_the_state_score_in_the_tick_function():
    load, files = aoe2mc.trigger_files([trig(aoe2mc.RESEARCHING_TECH)])
    assert "execute if score #p1.LOOM aoe_techstate matches 2 unless score #7 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/7" in files[TICK].splitlines()
    assert "scoreboard objectives add aoe_techstate dummy" in load


def test_technology_state_tests_its_state():
    _, files = aoe2mc.trigger_files([trig(aoe2mc.TECHNOLOGY_STATE, quantity=3)])
    assert "execute if score #p1.LOOM aoe_techstate matches 3 unless score #7 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/7" in files[TICK].splitlines()
    _, files = aoe2mc.trigger_files([trig(aoe2mc.TECHNOLOGY_STATE, quantity=-1)])   # disabled
    assert "aoe_techstate matches -1 " in files[TICK]


def test_gaia_or_no_technology_gives_no_trigger():
    for t in (trig(aoe2mc.RESEARCHING_TECH, player=0), trig(aoe2mc.TECHNOLOGY_STATE, tech="", quantity=3)):
        assert aoe2mc.trigger_files([t])[1] == {}


def test_the_pairs_of_the_conditions_go_into_aoe2mc_json():
    triggers = [trig(aoe2mc.RESEARCHING_TECH), dict(trig(aoe2mc.TECHNOLOGY_STATE, 2, "WHEELBARROW", quantity=3), id=8)]
    assert aoe2mc.tech_state_list(triggers) == [(1, "LOOM"), (2, "WHEELBARROW")]
    assert aoe2mc.tech_state_list([trig(aoe2mc.RESEARCHED)]) == []           # "Research Technology": aoe_tech


def test_the_scenario_mode_sets_the_state_of_the_technology():
    server, g, bot = game({"0": {}, "1": {}, "2": {}})
    g.data["tech_states"] = [[1, "LOOM"], [2, "LOOM"]]

    def states():
        g.tech_state_at = 0.0                                          # no wait of one second
        server.log.clear()
        scenario.tech_states(g)
        return [c for c in server.log if "aoe_techstate" in c]
    assert states() == ["scoreboard players set #p1.LOOM aoe_techstate 1",   # ready: the Dark Age technology
                        "scoreboard players set #p2.LOOM aoe_techstate 1"]
    assert states() == []                                              # one command per change
    rect = (0, 4, 0, 4)
    g.queues[rect] = [{"name": "LOOM"}]
    assert states() == ["scoreboard players set #p1.LOOM aoe_techstate 2"]   # researching
    g.queues[rect] = [{"name": "VILLAGER_MALE"}, {"name": "LOOM"}]
    assert states() == ["scoreboard players set #p1.LOOM aoe_techstate 4"]   # queued
    g.queues[rect] = []
    g.techs.add("LOOM")
    assert states() == ["scoreboard players set #p1.LOOM aoe_techstate 3"]   # researched


def test_a_technology_of_a_later_age_is_not_ready():
    assert scenario.tech_state(game({"0": {}, "1": {}})[1], "CHEMISTRY") == 0
