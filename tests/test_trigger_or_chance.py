"""#2815 (epic #2538): an "OR" trigger with a "Chance" group, and an "OR" timer of a disabled trigger that an
"Activate Trigger" effect turns on. A roll function sets the score #N.c<group> of aoe_trig once per second, and the
tick line of the group tests it; the activation starts the timer of each group (switch_lines, c.clocks)."""
from collections import Counter

import aoe2mc
from test_trigger_or import AREA, CHAT, OR, RUN

CHANCE = dict(type=aoe2mc.TRIGGER_CHANCE, timer=0, inverted=False, quantity=50)
TIMER = dict(type=aoe2mc.TIMER, timer=60, inverted=False)
FN = "data/aoe2mc/function/trigger/3"


def files(conds, looping=False, enabled=True, more=(), stats=None):
    t = dict(id=3, name="t", enabled=enabled, looping=looping, conditions=conds, effects=[CHAT])
    return aoe2mc.trigger_files([t, *more], stats=stats)


def test_chance_or_area_rolls_the_score_of_its_group_and_gives_two_tick_lines():
    stats = Counter()
    load, out = files([CHANCE, OR, AREA], stats=stats)
    assert "schedule function aoe2mc:trigger/3_c0 20t replace" in load
    assert out[f"{FN}_c0.mcfunction"].splitlines() == [
        "execute store result score #3.c0 aoe_trig run random value 1..100",
        "execute unless score #3 aoe_trig matches 1 run schedule function aoe2mc:trigger/3_c0 20t replace"]
    sel = aoe2mc.area_selector(AREA, 4)
    assert out["data/aoe2mc/function/tick.mcfunction"].splitlines() == [
        f"execute if score #3.c0 aoe_trig matches ..50 {RUN}", f"execute if entity {sel} {RUN}"]   # the same function
    assert out[f"{FN}.mcfunction"].splitlines()[-1] == "scoreboard players set #3 aoe_trig 1"
    assert "scoreboard objectives add aoe_trig dummy" in load and not any("not supported" in k for k in stats)


def test_a_looping_trigger_rolls_on_and_a_timer_in_the_other_group_has_its_score():
    load, out = files([AREA, OR, CHANCE, OR, TIMER], looping=True)
    assert out[f"{FN}_c1.mcfunction"].splitlines()[1] == "schedule function aoe2mc:trigger/3_c1 20t replace"
    assert "schedule function aoe2mc:trigger/3_t2 1200t replace" in load
    tick = out["data/aoe2mc/function/tick.mcfunction"].splitlines()
    assert f"execute if score #3.c1 aoe_trig matches ..50 {RUN}" in tick
    assert f"execute if score #3.t2 aoe_trig matches 1 {RUN}" in tick


def test_the_activation_of_a_disabled_or_timer_trigger_starts_the_timer_of_its_group():
    on = dict(id=4, name="on", enabled=True, looping=False, conditions=[dict(TIMER, timer=1)],
              effects=[dict(CHAT, type=aoe2mc.ACTIVATE_TRIGGER, trigger=3)])
    load, out = files([TIMER, OR, AREA], enabled=False, more=[on])
    assert not any("3_t0" in x for x in load)                          # not at the load: at the activation
    assert out[f"{FN}_t0.mcfunction"] == "scoreboard players set #3.t0 aoe_trig 1\n"
    assert out["data/aoe2mc/function/trigger/4.mcfunction"].splitlines()[:3] == [
        "scoreboard players reset #3 aoe_trig",
        "execute unless score #3 aoe_on matches 1 run scoreboard players reset #3.t0 aoe_trig",
        "execute unless score #3 aoe_on matches 1 run schedule function aoe2mc:trigger/3_t0 1200t replace"]
    assert out["data/aoe2mc/function/tick.mcfunction"].splitlines()[0] == \
        f"execute if score #3 aoe_on matches 1 if score #3.t0 aoe_trig matches 1 {RUN}"


def test_a_deactivation_clears_the_timer_of_the_group():
    off = dict(id=4, name="off", enabled=True, looping=False, conditions=[dict(TIMER, timer=1)],
               effects=[dict(CHAT, type=aoe2mc.DEACTIVATE_TRIGGER, trigger=3)])
    _, out = files([TIMER, OR, AREA], more=[off])
    assert "schedule clear aoe2mc:trigger/3_t0" in out["data/aoe2mc/function/trigger/4.mcfunction"].splitlines()
