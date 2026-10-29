"""#3891: a trigger with "Timer" AND a ticked condition (found in the check #3783). The timer is a schedule that sets the
score #N.t0 of aoe_trig, as in an "OR" group (#2791); the tick line tests it and the other condition. A trigger that
the converter cannot write is counted."""
from collections import Counter

import aoe2mc

CHAT = dict(type=aoe2mc.SEND_CHAT, message="Here.", player=1, time=0, object=None, tile=[-1, -1], area=[-1] * 4)
TIMER = dict(type=aoe2mc.TIMER, timer=4, inverted=False)
VICTORY = dict(type=aoe2mc.VICTORY_TIMER, inverted=True, player=1, quantity=20, comparison=0, timer_type=0)


def files(conds, enabled=True, looping=False, stats=None):
    t = dict(id=3, name="t", enabled=enabled, looping=looping, conditions=conds, effects=[CHAT])
    return aoe2mc.trigger_files([t], stats=stats)


def test_a_timer_and_a_victory_timer_make_a_tick_line_with_the_timer_score():
    load, fs = files([TIMER, VICTORY])
    assert fs["data/aoe2mc/function/tick.mcfunction"].splitlines() == [
        "execute if score #3.t0 aoe_trig matches 1 unless score #p1.0 aoe_vic matches 20 "
        "unless score #3 aoe_trig matches 1 run function aoe2mc:trigger/3"]
    assert fs["data/aoe2mc/function/trigger/3_t0.mcfunction"] == "scoreboard players set #3.t0 aoe_trig 1\n"
    assert "schedule function aoe2mc:trigger/3_t0 80t replace" in load


def test_a_timer_alone_stays_a_schedule():
    load, fs = files([TIMER])
    assert "data/aoe2mc/function/trigger/3_t0.mcfunction" not in fs
    assert "schedule function aoe2mc:trigger/3 80t replace" in load


def test_a_trigger_that_cannot_be_written_is_counted():
    stats = Counter()
    files([dict(type=aoe2mc.VICTORY_TIMER, inverted=False, player=0, quantity=20, comparison=0, timer_type=0)],
          stats=stats)
    assert stats["trigger conditions (not supported yet)"] == 1
