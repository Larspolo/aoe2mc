"""Triggers with the condition "Chance" roll once per second with `random value 1..100` (#2574)."""
import contextlib
import io
import shutil

from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios

ROLL = "data/aoe2mc/function/trigger/{}_chance.mcfunction"
TICK = "data/aoe2mc/function/tick.mcfunction"


def trig(id, chance=25, timer=None, area=None, looping=False):
    conds = [dict(type=aoe2mc.TRIGGER_CHANCE, timer=-1, inverted=False, quantity=chance)]
    conds += [dict(type=aoe2mc.TIMER, timer=timer, inverted=False)] if timer is not None else []
    conds += [dict(type=aoe2mc.IN_AREA, timer=-1, inverted=False, quantity=q, player=1, area=a)
              for q, a in area or []]
    return dict(id=id, name=f"t{id}", enabled=True, looping=looping, conditions=conds,
                effects=[dict(type=aoe2mc.SEND_CHAT, message="Lucky.", player=1, time=-1)])


def test_chance_alone_rolls_each_second_until_it_fires():
    load, files = aoe2mc.trigger_files([trig(1)])
    assert load == ["scoreboard objectives add aoe_trig dummy", "schedule function aoe2mc:trigger/1_chance 20t replace"]
    assert files[ROLL.format(1)].splitlines() == [
        "execute store result score #1.c aoe_trig run random value 1..100",
        "execute unless score #1 aoe_trig matches 1 run schedule function aoe2mc:trigger/1_chance 20t replace",
        "execute if score #1.c aoe_trig matches ..25 unless score #1 aoe_trig matches 1 run function aoe2mc:trigger/1"]
    assert files["data/aoe2mc/function/trigger/1.mcfunction"].splitlines() == [
        'tellraw @a {"text": "Lucky."}', "scoreboard players set #1 aoe_trig 1"]
    assert TICK not in files


def test_looping_chance_fires_again():
    _, files = aoe2mc.trigger_files([trig(2, 10, looping=True)])
    assert "aoe_trig 1" not in files["data/aoe2mc/function/trigger/2.mcfunction"]


def test_chance_with_an_area_fires_only_when_both_are_true():
    _, files = aoe2mc.trigger_files([trig(3, 50, area=[(1, [0, 0, 1, 1]), (2, [-1, -1, -1, -1])])], T=4)
    roll = files[ROLL.format(3)].splitlines()
    assert roll[2] == "execute store result score #3.2 aoe_trig if entity @e[tag=aoe2mc.p1,tag=!aoe2mc.mount]"
    assert roll[3] == ("execute if entity @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=0,y=-64,z=0,dx=7,dy=383,dz=7] "
                       "if score #3.2 aoe_trig matches 2.. if score #3.c aoe_trig matches ..50 "
                       "unless score #3 aoe_trig matches 1 run function aoe2mc:trigger/3")
    assert TICK not in files                                     # no check each tick: the roll checks the areas


def test_looping_chance_with_an_area_fires_again_after_the_units_leave():
    _, files = aoe2mc.trigger_files([trig(4, area=[(1, [0, 0, 1, 1])], looping=True)], T=4)
    assert files[ROLL.format(4)].splitlines()[1] == "schedule function aoe2mc:trigger/4_chance 20t replace"
    assert files[TICK].splitlines() == [
        "execute unless entity @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,x=0,y=-64,z=0,dx=7,dy=383,dz=7] "
        "run scoreboard players reset #4 aoe_trig"]


def test_chance_starts_after_the_timer():
    load, files = aoe2mc.trigger_files([trig(5, timer=30, looping=True)])
    assert load[1] == "schedule function aoe2mc:trigger/5_chance 600t replace"
    assert files["data/aoe2mc/function/trigger/5.mcfunction"].splitlines()[-1] == \
        "schedule function aoe2mc:trigger/5_chance 600t replace"         # a looping trigger waits for the timer again


def test_inverted_or_two_chances_are_not_supported():
    inverted, two = trig(6), trig(7)
    inverted["conditions"][0]["inverted"] = True
    two["conditions"].append(dict(two["conditions"][0]))
    assert aoe2mc.trigger_files([inverted, two]) == ([], {})


def test_scenario_chance_gives_its_percent(tmp_path):
    src = scenarios.triggers(str(tmp_path / "t.aoe2scenario"))
    shutil.copy(src, tmp_path / "read.aoe2scenario")              # the parser does not overwrite its source
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(str(tmp_path / "read.aoe2scenario"))
    t = scn.trigger_manager.add_trigger("Lucky")
    t.new_condition.chance(quantity=25)
    t.new_effect.send_chat(source_player=PlayerId.ONE, message="Lucky.")
    out = scenarios.save(scn, str(tmp_path / "c.aoe2scenario"))
    texts = aoe2mc.read_scenario(out)[4]
    assert texts["triggers"][-1]["conditions"][0]["quantity"] == 25
    load, files = aoe2mc.trigger_files(texts["triggers"])
    n = texts["triggers"][-1]["id"]
    assert f"if score #{n}.c aoe_trig matches ..25" in files[ROLL.format(n)]
