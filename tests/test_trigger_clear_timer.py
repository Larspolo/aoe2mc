"""The trigger effect "Clear Timer" removes the boss bar and the count of a "Display Timer" slot (#2696)."""
import contextlib
import io
from collections import Counter

import aoe2mc
from tools import scenarios


def timer_trigger(id, effect):
    return dict(id=id, name=f"t{id}", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=10, inverted=False)], effects=[effect])


DISPLAY = dict(type=aoe2mc.DISPLAY_TIMER, message="Reinforcements in %d s", player=-1, time=60, unit=2, timer=3)
CLEAR = dict(type=aoe2mc.CLEAR_TIMER, message="", player=-1, time=0, timer=3)


def test_clear_timer_removes_the_bar_and_the_count_of_its_slot():
    stats = Counter()
    load, files = aoe2mc.trigger_files([timer_trigger(4, DISPLAY), timer_trigger(5, CLEAR)], stats=stats)
    assert files["data/aoe2mc/function/trigger/5.mcfunction"].splitlines() == [
        "bossbar remove aoe2mc:timer3", "schedule clear aoe2mc:timer/3"]
    assert stats["clear timer"] == 1


def test_clear_timer_of_a_slot_no_trigger_uses_still_names_its_bar():
    _, files = aoe2mc.trigger_files([timer_trigger(5, dict(CLEAR, timer=7))])
    assert files["data/aoe2mc/function/trigger/5.mcfunction"].splitlines() == [
        "bossbar remove aoe2mc:timer7", "schedule clear aoe2mc:timer/7"]


def test_read_scenario_keeps_the_slot(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Clear")
    t.new_condition.timer(timer=1)
    t.new_effect.clear_timer(timer=3)
    src = scenarios.save(scn, str(tmp_path / "c.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    e, = trigger["effects"]
    assert e["type"] == aoe2mc.CLEAR_TIMER and e["timer"] == 3
