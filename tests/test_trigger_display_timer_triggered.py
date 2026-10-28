"""The condition "Display Timer Triggered" fires when the timer of its slot reaches 0 (#2702): the timer sets the score
#done<slot> of aoe_timer at 0, and the tick function tests it. A new timer of the slot resets the score."""
import aoe2mc

TIMER = dict(type=aoe2mc.DISPLAY_TIMER, message="Attack in %d s", player=-1, time=60, unit=2, timer=3)
CHAT = dict(type=aoe2mc.SEND_CHAT, message="Time is up.", player=1, time=0, object=None, tile=[-1, -1], area=[-1] * 4)


def files(conds, effects=(TIMER,)):
    trig = dict(id=5, name="t5", enabled=True, looping=False, conditions=conds, effects=[CHAT] if not effects else list(effects))
    return aoe2mc.trigger_files([trig])[1]


def display_timer_triggered(slot=3):
    return dict(type=aoe2mc.DISPLAY_TIMER_TRIGGERED, timer=0, inverted=False, slot=slot)


def test_the_timer_sets_the_score_at_zero_and_the_tick_function_tests_it():
    f = files([display_timer_triggered()])
    timer = f["data/aoe2mc/function/timer/3.mcfunction"].splitlines()
    assert "execute if score #t3 aoe_timer matches ..0 run scoreboard players set #done3 aoe_timer 1" in timer
    assert f["data/aoe2mc/function/tick.mcfunction"].splitlines() == [
        "execute if score #done3 aoe_timer matches 1.. unless score #5 aoe_trig matches 1 run function aoe2mc:trigger/5"]


def test_a_new_timer_of_the_slot_resets_the_score():
    f = files([display_timer_triggered()])
    assert "scoreboard players reset #done3 aoe_timer" in f["data/aoe2mc/function/trigger/5.mcfunction"].splitlines()


def test_another_slot_has_its_own_score():
    f = files([display_timer_triggered(slot=2)])
    assert "#done2 aoe_timer matches 1.." in f["data/aoe2mc/function/tick.mcfunction"]
