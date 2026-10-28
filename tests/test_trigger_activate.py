"""Triggers turn other triggers on and off with "Activate Trigger" and "Deactivate Trigger" (#2575)."""
import contextlib
import io

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios

FN = "data/aoe2mc/function/trigger/{}.mcfunction"
TICK = "data/aoe2mc/function/tick.mcfunction"


def trig(id, conds, effects, enabled=True, looping=False):
    return dict(id=id, name=f"t{id}", enabled=enabled, looping=looping,
                conditions=[dict(type=t, timer=s, inverted=False, quantity=1, player=1, area=[0, 0, 1, 1])
                            for t, s in conds],
                effects=[dict(type=t, message=m, player=1, time=-1, **({"trigger": k} if k is not None else {}))
                         for t, m, k in effects])


def test_activate_starts_the_timer_of_a_disabled_trigger():
    first = trig(0, [(aoe2mc.TIMER, 5)], [(aoe2mc.ACTIVATE_TRIGGER, "", 1)])
    second = trig(1, [(aoe2mc.TIMER, 10)], [(aoe2mc.SEND_CHAT, "Second.", None)], enabled=False)
    load, files = aoe2mc.trigger_files([first, second])
    assert load == ["scoreboard objectives add aoe_on dummy", "schedule function aoe2mc:trigger/0 100t replace"]
    assert files[FN.format(0)].splitlines() == [
        "execute unless score #1 aoe_on matches 1 run schedule function aoe2mc:trigger/1 200t replace",
        "scoreboard players set #1 aoe_on 1"]
    assert files[FN.format(1)].splitlines() == ['tellraw @a {"text": "Second."}', "scoreboard players set #1 aoe_on 0"]


def test_deactivate_turns_an_area_trigger_off():
    timer = trig(0, [(aoe2mc.TIMER, 5)], [(aoe2mc.DEACTIVATE_TRIGGER, "", 1)])
    area = trig(1, [(aoe2mc.IN_AREA, -1)], [(aoe2mc.SEND_CHAT, "In the area.", None)])
    load, files = aoe2mc.trigger_files([timer, area], T=1)
    assert files[FN.format(0)].splitlines() == ["scoreboard players set #1 aoe_on 0"]
    assert "scoreboard players set #1 aoe_on 1" in load                # enabled: on at the start
    assert files[TICK].startswith("execute if score #1 aoe_on matches 1 if entity @e[")


def test_deactivate_clears_the_timer():
    _, files = aoe2mc.trigger_files([trig(0, [(aoe2mc.TIMER, 1)], [(aoe2mc.DEACTIVATE_TRIGGER, "", 1)]),
                                     trig(1, [(aoe2mc.TIMER, 9)], [(aoe2mc.SEND_CHAT, "x", None)], looping=True)])
    assert files[FN.format(0)].splitlines() == ["schedule clear aoe2mc:trigger/1", "scoreboard players set #1 aoe_on 0"]
    assert "aoe_on 0" not in files[FN.format(1)]                         # a looping trigger stays on after it fires


def test_disabled_trigger_that_nothing_activates_gives_no_file():
    triggers = [trig(0, [(aoe2mc.TIMER, 5)], [(aoe2mc.SEND_CHAT, "a", None)], enabled=False),
                trig(1, [(aoe2mc.TIMER, 5)], [(aoe2mc.DEACTIVATE_TRIGGER, "", 0)], enabled=False)]
    assert aoe2mc.trigger_files(triggers) == ([], {})


def test_activate_of_a_trigger_with_no_file_gives_no_line():
    load, files = aoe2mc.trigger_files([trig(0, [(aoe2mc.TIMER, 5)], [(aoe2mc.ACTIVATE_TRIGGER, "", 1),
                                                                      (aoe2mc.SEND_CHAT, "a", None)]),
                                        trig(1, [(aoe2mc.TIMER, 5)], [(aoe2mc.SEND_CHAT, "", None)], enabled=False)])
    assert list(files) == [FN.format(0)] and "aoe_on" not in files[FN.format(0)] + "".join(load)


def test_scenario_effect_gives_its_target(tmp_path):
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(tmp_path / "tiny.aoe2scenario")))
    tm = scn.trigger_manager
    t = tm.add_trigger("Start")
    t.new_condition.timer(timer=5)
    t.new_effect.activate_trigger(trigger_id=1)
    t = tm.add_trigger("Later", enabled=False)
    t.new_condition.timer(timer=3)
    t.new_effect.send_chat(source_player=1, message="Later.")
    path = scenarios.save(scn, str(tmp_path / "a.aoe2scenario"))
    first, later = aoe2mc.read_scenario(path)[4]["triggers"]
    assert first["effects"][0]["trigger"] == 1 and "trigger" not in later["effects"][0]
    load, files = aoe2mc.trigger_files([first, later])
    assert "schedule function aoe2mc:trigger/1 60t replace" in files[FN.format(0)]
