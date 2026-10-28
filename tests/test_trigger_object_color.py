"""The trigger effect "Change Object Player Color" gives the names of the units in its area the color of another player
color (#2824); the owner and the team stay."""
import contextlib
import io
import os

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios

AREA = f"x=4,y={aoe2mc.MIN_Y},z=8,dx=7,dy={aoe2mc.HEIGHT - 1},dz=7"         # tiles 1..2, 2..3 at T = 4


def trig(player=1, color=2, area=(1, 2, 2, 3)):
    return dict(id=5, name="t5", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)],
                effects=[dict(type=aoe2mc.CHANGE_OBJECT_PLAYER_COLOR, message="", player=player, time=-1, object=None,
                              tile=[-1, -1], area=list(area), color=color)])


def lines(**k):
    files = aoe2mc.trigger_files([trig(**k)], T=4)[1]
    return files.get("data/aoe2mc/function/trigger/5.mcfunction", "").splitlines()


def test_the_names_of_the_units_in_the_area_get_red():
    assert lines() == [f"execute as @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,{AREA}] run data modify entity @s "
                       f"CustomName.color set value \"#E0281E\""]          # PlayerColorId 2: red, units.HEX
    assert lines(player=3, color=6)[0].endswith("CustomName.color set value \"#A000F0\"")   # 6: purple


def test_a_color_outside_1_to_8_writes_no_command():
    assert lines(color=0) == lines(color=9) == lines(color=None) == []


def test_the_effect_is_read_and_converted(tmp_path):
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(tmp_path / "t.aoe2scenario")))
    t = scn.trigger_manager.add_trigger("Red names")
    t.new_condition.timer(timer=10)
    t.new_effect.change_object_player_color(source_player=1, player_color=2, area_x1=1, area_y1=2, area_x2=2, area_y2=3)
    src = scenarios.save(scn, str(tmp_path / "c.aoe2scenario"))
    (red,) = aoe2mc.read_scenario(src)[4]["triggers"]
    assert red["effects"][0]["color"] == 2 and red["effects"][0]["player"] == 1
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    fn = os.path.join(tmp_path, "W", "datapacks", "aoe2mc", "data", "aoe2mc", "function")
    with open(os.path.join(fn, "trigger", f"{red['id']}.mcfunction")) as f:
        assert f"{AREA}] run data modify entity @s CustomName.color set value \"#E0281E\"" in f.read()
