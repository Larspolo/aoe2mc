"""The trigger effect "Change Player Color" gives the team of a player the chat color of the new color (#2712)."""
import contextlib
import io
import os

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios


def trig(player=1, color=2):
    return dict(id=5, name="t5", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)],
                effects=[dict(type=aoe2mc.CHANGE_PLAYER_COLOR, message="", player=player, time=-1, object=None,
                              tile=[-1, -1], area=[-1, -1, -1, -1], color=color)])


def lines(**k):
    files = aoe2mc.trigger_files([trig(**k)], T=4)[1]
    return files.get("data/aoe2mc/function/trigger/5.mcfunction", "").splitlines()


def test_player_1_gets_red():
    assert lines() == ["team modify p1 color red"]
    assert lines(player=3, color=6) == ["team modify p3 color dark_purple"]    # PlayerColorId 6: purple


def test_gaia_and_an_unknown_color_write_no_command():
    assert lines(player=0) == lines(color=0) == lines(color=9) == lines(color=None) == []


def color_scenario(path):
    """The tiny map with a timer trigger at 10 s that makes player 1 red."""
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(path.with_suffix(".tiny"))))
    t = scn.trigger_manager.add_trigger("Red")
    t.new_condition.timer(timer=10)
    t.new_effect.change_player_color(source_player=1, player_color=2)
    return scenarios.save(scn, str(path))


def test_the_effect_is_read_and_converted(tmp_path):
    src = color_scenario(tmp_path / "c.aoe2scenario")
    (red,) = aoe2mc.read_scenario(src)[4]["triggers"]
    assert red["effects"][0]["color"] == 2 and red["effects"][0]["player"] == 1
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    fn = os.path.join(tmp_path, "W", "datapacks", "aoe2mc", "data", "aoe2mc", "function")
    with open(os.path.join(fn, "trigger", f"{red['id']}.mcfunction")) as f:
        assert "team modify p1 color red" in f.read().splitlines()
