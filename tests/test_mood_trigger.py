"""The trigger effect "Change Color Mood" changes the time of day and the rain of the world (#1876)."""
import contextlib
import io
import os

from AoE2ScenarioParser.datasets.trigger_lists import ColorMood
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios


def trig(mood):
    return dict(id=4, name="t4", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)],
                effects=[dict(type=aoe2mc.CHANGE_COLOR_MOOD, message="", player=-1, time=-1, mood=mood)])


def lines(mood, on=True):
    files = aoe2mc.trigger_files([trig(mood)], mood=on)[1]
    return files.get("data/aoe2mc/function/trigger/4.mcfunction", "").splitlines()


def expect(mood):
    """The commands of a mood from the tables of the converter: its time (MOODS) and its rain (RAIN)."""
    return [f"time set {aoe2mc.MOODS[mood]}", "weather rain" if mood in aoe2mc.RAIN else "weather clear"]


def test_night_and_swamp_set_the_time_and_the_weather():
    for mood in ("NIGHT", "SWAMP", "EVENING"):
        assert lines(mood) == expect(mood), mood


def test_mood_off_and_unknown_moods_write_no_command():
    assert lines("NIGHT", on=False) == [] and lines(None) == []


def mood_scenario(path):
    """The tiny map with a timer trigger at 20 s that changes the color mood to Swamp (the parser does not overwrite
    the file that it read)."""
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(path.with_suffix(".tiny"))))
    t = scn.trigger_manager.add_trigger("Storm")
    t.new_condition.timer(timer=20)
    t.new_effect.change_color_mood(color_mood=ColorMood.SWAMP)
    return scenarios.save(scn, str(path))


def test_the_effect_is_read_and_converted(tmp_path):
    src = mood_scenario(tmp_path / "m.aoe2scenario")
    (storm,) = aoe2mc.read_scenario(src)[4]["triggers"]
    assert storm["effects"][0]["mood"] == "SWAMP"
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    fn = os.path.join(tmp_path, "W", "datapacks", "aoe2mc", "data", "aoe2mc", "function")
    with open(os.path.join(fn, "start.mcfunction")) as f:
        assert f"schedule function aoe2mc:trigger/{storm['id']} 400t replace" in f.read()
    with open(os.path.join(fn, "trigger", f"{storm['id']}.mcfunction")) as f:
        assert f.read().splitlines() == expect("SWAMP")
