"""#2699 (epic #2538): the condition "Trigger Active" fires a trigger while another one is on: the score #N of aoe_on
(the state of trigger N, aoe2mc.trigger_files). An inverted condition fires it while the other one is off."""
import aoe2mc

TICK = "data/aoe2mc/function/tick.mcfunction"
FN = "data/aoe2mc/function/trigger/{}.mcfunction"


def trig(id, conds, effects, enabled=True, looping=False):
    return dict(id=id, name=f"t{id}", enabled=enabled, looping=looping,
                conditions=[dict(type=t, timer=0, inverted=False) | x for t, x in conds],
                effects=[dict(message="", time=-1, object=None, tile=[-1, -1], area=[-1] * 4) | e for e in effects])


def first(enabled=True):
    """Trigger 1: a timer and a change of variable 1; it has a function, so it has a state score."""
    return trig(1, [(aoe2mc.TIMER, dict(timer=5))], [dict(type=aoe2mc.CHANGE_VARIABLE, variable=1, operation=1,
                                                          quantity=5)], enabled=enabled)


def second(inverted=False):
    """Trigger 2 fires while trigger 1 is on (or off when inverted) and changes variable 2."""
    return trig(2, [(aoe2mc.TRIGGER_ACTIVE, dict(trigger=1, inverted=inverted))],
                [dict(type=aoe2mc.CHANGE_VARIABLE, variable=2, operation=1, quantity=7)], looping=True)


def test_the_state_score_of_trigger_1_is_tested_in_the_tick_function():
    load, files = aoe2mc.trigger_files([first(), second()])
    assert "scoreboard players set #1 aoe_on 1" in load                    # enabled: on at the start
    assert "scoreboard objectives add aoe_on dummy" in load
    assert files[TICK].splitlines() == [
        "execute if score #1 aoe_on matches 1 unless score #2 aoe_trig matches 1 run function aoe2mc:trigger/2",
        "execute unless score #1 aoe_on matches 1 run scoreboard players reset #2 aoe_trig"]


def test_an_inverted_condition_tests_the_score_at_0():
    load, files = aoe2mc.trigger_files([first(), second(inverted=True)])
    assert files[TICK].splitlines()[0] == \
        "execute if score #1 aoe_on matches 0 unless score #2 aoe_trig matches 1 run function aoe2mc:trigger/2"


def test_an_inverted_condition_on_a_disabled_trigger_sets_its_score_to_0():
    load, files = aoe2mc.trigger_files([first(enabled=False), second(inverted=True)])
    assert "scoreboard players set #1 aoe_on 0" in load                   # off at the start, so the test can fire
    assert "scoreboard players set #1 aoe_on 1" not in load


def test_a_condition_on_a_trigger_without_a_function_writes_no_test():
    load, files = aoe2mc.trigger_files([second()])                          # trigger 1 is not in the world
    assert TICK not in files and FN.format(2) not in files
