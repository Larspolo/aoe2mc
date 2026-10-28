"""Triggers with the conditions "Own Objects" and "Own Fewer Objects" fire when the player has at least (or at most) the
number of units of the condition on the whole map (#2573)."""
import contextlib
import io

from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios

TICK = "data/aoe2mc/function/tick.mcfunction"


def own(id, kind, player, quantity, looping=False):
    return dict(id=id, name=f"t{id}", enabled=True, looping=looping,
                conditions=[dict(type=kind, timer=-1, inverted=False, quantity=quantity, player=player,
                                 area=[-1, -1, -1, -1], object=-1, group=-1, **{"class": -1})],
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Enough units.", player=1, time=-1)])


def test_own_objects_counts_the_units_of_the_player():
    _, files = aoe2mc.trigger_files([own(1, aoe2mc.OWN_OBJECTS, 1, 5)], T=4)
    assert files[TICK].splitlines() == [
        "execute store result score #1.0 aoe_trig if entity @e[tag=aoe2mc.p1,tag=!aoe2mc.mount]",
        "execute if score #1.0 aoe_trig matches 5.. unless score #1 aoe_trig matches 1 run function aoe2mc:trigger/1"]
    assert files["data/aoe2mc/function/trigger/1.mcfunction"].splitlines() == [
        'tellraw @a {"text": "Enough units."}', "scoreboard players set #1 aoe_trig 1"]


def test_own_fewer_objects_fires_at_the_quantity_or_fewer():
    _, files = aoe2mc.trigger_files([own(2, aoe2mc.OWN_FEWER_OBJECTS, 2, 2, looping=True)], T=4)
    lines = files[TICK].splitlines()
    assert lines[0] == "execute store result score #2.0 aoe_trig if entity @e[tag=aoe2mc.p2,tag=!aoe2mc.mount]"
    assert lines[1] == "execute if score #2.0 aoe_trig matches ..2 unless score #2 aoe_trig matches 1 run function aoe2mc:trigger/2"
    assert lines[2] == "execute unless score #2.0 aoe_trig matches ..2 run scoreboard players reset #2 aoe_trig"


def test_own_objects_with_an_area_condition_and_the_whole_map():
    t = own(3, aoe2mc.OWN_OBJECTS, 1, 1)
    t["conditions"][0]["area"] = [0, 0, 1, 1]                          # the condition has no area in AoE2
    t["conditions"].append(dict(type=aoe2mc.IN_AREA, timer=-1, inverted=False, quantity=1, player=2, area=[0, 0, 1, 1]))
    _, files = aoe2mc.trigger_files([t], T=4)
    assert files[TICK] == ("execute if entity @e[tag=aoe2mc.p1,tag=!aoe2mc.mount] "
                           "if entity @e[tag=aoe2mc.p2,tag=!aoe2mc.mount,x=0,y=-64,z=0,dx=7,dy=383,dz=7] "
                           "unless score #3 aoe_trig matches 1 run function aoe2mc:trigger/3\n")


def test_read_scenario_keeps_the_player_and_the_quantity(tmp_path):
    path = scenarios.triggers(str(tmp_path / "t.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(path)
        t = scn.trigger_manager.add_trigger("Army")
        t.new_condition.own_objects(quantity=5, source_player=PlayerId.TWO)
        t.new_condition.own_fewer_objects(quantity=2, source_player=PlayerId.ONE)
        t.new_effect.send_chat(source_player=PlayerId.ONE, message="Army.")
    texts = aoe2mc.read_scenario(scenarios.save(scn, str(tmp_path / "own.aoe2scenario")))[4]
    conds = texts["triggers"][-1]["conditions"]
    assert [(c["type"], c["player"], c["quantity"]) for c in conds] == [
        (aoe2mc.OWN_OBJECTS, 2, 5), (aoe2mc.OWN_FEWER_OBJECTS, 1, 2)]
    _, files = aoe2mc.trigger_files(texts["triggers"], T=4)
    assert f"if score #{texts['triggers'][-1]['id']}.0 aoe_trig matches 5.." in files[TICK]
