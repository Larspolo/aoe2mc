"""#2791 (epic #2538): a trigger whose "OR" groups have a "Timer" fires in the converted world, as in AoE2 DE ("Timer 60,
OR, Objects in Area"): a schedule sets the score #N.t<group> of aoe_trig, and the tick line of the group tests it."""
import aoe2mc
from test_trigger_or import AREA, CHAT, OR, RUN, VALUE

TIMER = dict(type=aoe2mc.TIMER, timer=60, inverted=False)
FN = "data/aoe2mc/function/trigger/3"


def files(conds, looping=False, enabled=True, stats=None):
    t = dict(id=3, name="t", enabled=enabled, looping=looping, conditions=conds, effects=[CHAT])
    return aoe2mc.trigger_files([t], stats=stats)


def test_timer_or_area_gives_a_schedule_that_sets_a_score_and_two_tick_lines():
    load, out = files([TIMER, OR, AREA])
    assert "schedule function aoe2mc:trigger/3_t0 1200t replace" in load
    assert out[f"{FN}_t0.mcfunction"] == "scoreboard players set #3.t0 aoe_trig 1\n"
    sel = aoe2mc.area_selector(AREA, 4)
    assert out["data/aoe2mc/function/tick.mcfunction"].splitlines() == [
        f"execute if score #3.t0 aoe_trig matches 1 {RUN}", f"execute if entity {sel} {RUN}"]   # the same function


def test_the_trigger_runs_once_when_both_groups_hold():
    _, out = files([TIMER, OR, AREA])
    assert out[f"{FN}.mcfunction"].splitlines()[-1] == "scoreboard players set #3 aoe_trig 1"   # the next line skips


def test_a_timer_and_a_condition_in_one_group_both_count():
    _, out = files([TIMER, VALUE, OR, AREA])
    assert out["data/aoe2mc/function/tick.mcfunction"].splitlines()[0] == \
        f"execute if score #3.t0 aoe_trig matches 1 if score #v2 aoe_var matches 3.. {RUN}"


def test_a_looping_trigger_starts_its_timer_again_and_fires_after_no_group_holds():
    _, out = files([AREA, OR, TIMER], looping=True)
    fn = out[f"{FN}.mcfunction"].splitlines()
    assert fn[-3:] == ["scoreboard players reset #3.t1 aoe_trig", "schedule function aoe2mc:trigger/3_t1 1200t replace",
                       "scoreboard players set #3 aoe_trig 1"]
    tick = out["data/aoe2mc/function/tick.mcfunction"].splitlines()
    assert "execute if score #3.t1 aoe_trig matches 1 run scoreboard players set #3.or aoe_trig 1" in tick
    assert tick[-1] == "execute if score #3.or aoe_trig matches 0 run scoreboard players reset #3 aoe_trig"


def test_or_of_timers_fires_at_the_first_group():
    load, out = files([dict(TIMER, timer=90), OR, TIMER])
    assert load[-1] == "schedule function aoe2mc:trigger/3 1200t replace"   # 60 s, not 90 s
    assert "data/aoe2mc/function/tick.mcfunction" not in out
