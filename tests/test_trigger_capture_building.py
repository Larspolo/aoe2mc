"""#2940 (epic #2538): a trigger with the condition "Capture Object" on a building fires in the scenario mode when the
player of the condition owns the building. The converter tests the score #o<ref> of aoe_owner; the game program sets
it to the owner of the building in aoe2mc.json (game/scenario.py owners). A unit keeps the tag test (#2619)."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import aoe2mc  # noqa: E402
import gather  # noqa: E402
import scenario  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402

BUILDING = {"kind": "building", "name": "CASTLE", "player": 1, "ref": 7, "footprint": [4, 4, 8, 8]}


def capture(ref=7, player=2, inverted=False, unit=False):
    return dict(type=aoe2mc.CAPTURE_OBJECT, timer=0, inverted=inverted, ref=ref, player=player, unit=unit)


def trig(conds):
    return dict(id=5, name="t", enabled=True, looping=False, conditions=conds,
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Captured!", player=1, time=0, object=None,
                              tile=[-1, -1], area=[-1] * 4)])


def tick(conds):
    return aoe2mc.trigger_files([trig(conds)])[1]["data/aoe2mc/function/tick.mcfunction"].splitlines()


def test_the_condition_tests_the_owner_score_of_the_building_in_the_tick_function():
    assert tick([capture()]) == ["execute if score #o7 aoe_owner matches 2 unless score #5 aoe_trig matches 1 "
                                 "run function aoe2mc:trigger/5"]


def test_an_inverted_condition_holds_while_another_player_owns_the_building():
    assert "execute unless score #o7 aoe_owner matches 2 unless score #5 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/5" in tick([capture(inverted=True)])


def test_a_unit_keeps_the_tag_test():
    assert tick([capture(unit=True)])[0].startswith("execute if entity @e[tag=aoe2mc.r7,tag=aoe2mc.p2] ")


def test_a_tick_function_lists_the_refs_of_the_buildings_for_the_game_program():
    triggers = [trig([capture(ref=7)]), trig([capture(ref=3)])]
    assert aoe2mc.owner_list(triggers) == [3, 7]
    assert "scoreboard objectives add aoe_owner dummy" in aoe2mc.trigger_files(triggers)[0]


def test_the_scenario_mode_sets_the_score_each_time_the_owner_changes():
    server = FakeServer({})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], [dict(BUILDING)])).setup()
    g.data["owners"] = [7]
    scenario.owners(g)
    assert [c for c in server.log if "aoe_owner" in c] == ["scoreboard players set #o7 aoe_owner 1"]
    next(o for o in g.data["objects"] if o.get("ref") == 7)["player"] = 2    # a monk converts it (monk.win)
    for _ in range(2):
        g.owners_at = 0.0
        scenario.owners(g)
    assert [c for c in server.log if "aoe_owner" in c][1:] == ["scoreboard players set #o7 aoe_owner 2"]   # once
