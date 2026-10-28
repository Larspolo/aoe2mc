"""#2714 (epic #2538): a trigger with the condition "Units Garrisoned" fires in the scenario mode when its building
holds at least the number of units of the condition. The game program sets the score #g<ref> of aoe_gar to the number
of units inside, and the tick function of the datapack tests it."""
import contextlib
import io
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import aoe2mc  # noqa: E402
import garrison  # noqa: E402
import gather  # noqa: E402
import scenario  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402

from tools import scenarios  # noqa: E402

TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "ref": 12, "footprint": [4, 4, 8, 8]}
RECT = (4, 8, 4, 8)                                                     # (x0, x1, z0, z1) of garrison.holders


def trig(ref=12, quantity=3):
    return dict(id=7, name="t", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.UNITS_GARRISONED, timer=0, inverted=False, quantity=quantity, unit=ref)],
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Full!", player=1, time=0, object=None, tile=[-1, -1],
                              area=[-1] * 4)])


def test_the_condition_tests_the_score_of_the_building_in_the_tick_function():
    load, files = aoe2mc.trigger_files([trig()])
    assert "execute if score #g12 aoe_gar matches 3.. unless score #7 aoe_trig matches 1 run function " \
           "aoe2mc:trigger/7" in files["data/aoe2mc/function/tick.mcfunction"].splitlines()
    assert "scoreboard objectives add aoe_gar dummy" in load


def test_no_building_gives_no_trigger():
    assert aoe2mc.trigger_files([trig(ref=-1)])[1] == {}


def test_the_scenario_mode_sets_the_number_of_units_inside():
    units = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{k}", "tile": [10.5 + k, 10.5]}
             for k in range(3)]
    server = FakeServer({u["uuid"]: {"Pos": (u["tile"][0], 64.0, u["tile"][1])} for u in units})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], [TC] + units)).setup()
    g.bots = [types.SimpleNamespace(g=gather.Gather(server, grid([[64] * 16 for _ in range(16)], []), player=2))]
    scenario.garrisons(g)
    assert not [c for c in server.log if " aoe_gar " in c]               # empty: no score, no command
    for u in ("v0", "v1", "v2"):
        garrison.go_in(g, u, RECT, TC)
    scenario.garrisons(g)
    scenario.garrisons(g)
    assert [c for c in server.log if " aoe_gar " in c] == ["scoreboard players set #g12 aoe_gar 3"]   # once
    g.garrisons[RECT].remove("v2")                                     # a unit that leaves the building
    scenario.garrisons(g)
    assert server.log[-1] == "scoreboard players set #g12 aoe_gar 2"
    garrison.out(g, RECT)
    scenario.garrisons(g)
    assert server.log[-1] == "scoreboard players set #g12 aoe_gar 0"


def test_read_scenario_keeps_the_building_and_the_quantity(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Full")
    t.new_condition.units_garrisoned(quantity=3, unit_object=12)
    t.new_effect.send_chat(source_player=1, message="Full!")
    src = scenarios.save(scn, str(tmp_path / "g.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    c, = trigger["conditions"]
    assert c["type"] == aoe2mc.UNITS_GARRISONED and c["quantity"] == 3 and c["unit"] == 12
