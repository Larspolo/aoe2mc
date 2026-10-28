"""The trigger effect "Display Timer" shows a boss bar with its text and the time left (#2572)."""
import contextlib
import io
import json
import os
import sys

from AoE2ScenarioParser.datasets.trigger_lists import TimeUnit
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import wonder  # noqa: E402

TICK = "data/aoe2mc/function/timer/3.mcfunction"


def trig(time=60, unit=2, message="Reinforcements in %d s"):
    return dict(id=4, name="t4", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=10, inverted=False)],
                effects=[dict(type=aoe2mc.DISPLAY_TIMER, message=message, player=-1, time=time, unit=unit, timer=3)])


def files(**kw):
    return aoe2mc.trigger_files([trig(**kw)])[1]


def name(lines):
    return json.loads(next(c for c in lines if c.startswith("bossbar set aoe2mc:timer3 name "))
                      .removeprefix("bossbar set aoe2mc:timer3 name "))


def test_a_timer_of_60_seconds_adds_a_bar_and_a_count_down():
    f = files()
    start = f["data/aoe2mc/function/trigger/4.mcfunction"].splitlines()
    assert {"bossbar add aoe2mc:timer3 \"\"", "bossbar set aoe2mc:timer3 max 60", "bossbar set aoe2mc:timer3 players @a",
            "scoreboard players set #t3 aoe_timer 60", "schedule function aoe2mc:timer/3 1s replace"} <= set(start)
    tick = f[TICK].splitlines()
    assert tick[0] == "scoreboard players remove #t3 aoe_timer 1"
    assert "execute store result bossbar aoe2mc:timer3 value run scoreboard players get #t3 aoe_timer" in tick
    assert "execute if score #t3 aoe_timer matches ..0 run bossbar remove aoe2mc:timer3" in tick
    assert "execute if score #t3 aoe_timer matches 1.. run schedule function aoe2mc:timer/3 1s replace" in tick


def test_the_text_shows_the_time_left_in_place_of_d():
    left = {"score": {"name": "#t3", "objective": "aoe_timer"}}
    assert name(files()[TICK].splitlines()) == [{"text": "Reinforcements in "}, left, {"text": " s"}]
    assert name(files(message="<RED>No time")[TICK].splitlines()) == [{"text": "No time"}, {"text": ""}]


def test_minutes_and_years_count_in_game_seconds_and_show_their_unit():
    for unit, sec in ((TimeUnit.MINUTES, 120), (TimeUnit.YEARS, 2 * wonder.YEAR)):
        start = files(time=2, unit=unit.value)["data/aoe2mc/function/trigger/4.mcfunction"].splitlines()
        assert f"bossbar set aoe2mc:timer3 max {int(sec)}" in start
        assert f"scoreboard players set #d3 aoe_timer {int(sec) // 2}" in start     # the seconds of one unit
    tick = files(time=90, unit=TimeUnit.MINUTES_AND_SECONDS.value, message="%d")[TICK].splitlines()
    assert [p.get("score", {}).get("name") for p in name(tick)] == [None, "#m3", None, "#z3", "#s3", None]


def timer_scenario(path):
    """The tiny map with a timer trigger at 5 s that shows a timer of 30 s."""
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(path.with_suffix(".tiny"))))
    t = scn.trigger_manager.add_trigger("Count")
    t.new_condition.timer(timer=5)
    t.new_effect.display_timer(display_time=30, time_unit=TimeUnit.SECONDS, timer=2, message="Wave in %d")
    return scenarios.save(scn, str(path))


def test_the_effect_is_read_and_converted(tmp_path):
    src = timer_scenario(tmp_path / "t.aoe2scenario")
    (count,) = aoe2mc.read_scenario(src)[4]["triggers"]
    e = count["effects"][0]
    assert (e["unit"], e["timer"], e["time"]) == (TimeUnit.SECONDS.value, 2, 30)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    fn = os.path.join(tmp_path, "W", "datapacks", "aoe2mc", "data", "aoe2mc", "function")
    with open(os.path.join(fn, "trigger", f"{count['id']}.mcfunction")) as f:
        assert "bossbar set aoe2mc:timer2 max 30" in f.read()
    assert os.path.exists(os.path.join(fn, "timer", "2.mcfunction"))
