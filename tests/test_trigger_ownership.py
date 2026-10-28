"""The trigger effect "Change Ownership" gives the units of a player in an area to another player (#2570): they get
the tag aoe2mc.p<new> and the team p<new>, and lose the tag aoe2mc.p<old>."""
import contextlib
import io
import os

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios


def trig(player=1, target=2):
    return dict(id=5, name="t5", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)],
                effects=[dict(type=aoe2mc.CHANGE_OWNERSHIP, message="", player=player, time=-1, object=None,
                              tile=[-1, -1], area=[2, 3, 4, 5], target=target)])


def lines(**k):
    files = aoe2mc.trigger_files([trig(**k)], T=4)[1]
    return files.get("data/aoe2mc/function/trigger/5.mcfunction", "").splitlines()


def test_the_units_of_player_1_in_the_area_go_to_player_2():
    sel = aoe2mc.area_selector(trig()["effects"][0], 4)
    assert "tag=aoe2mc.p1" in sel and "x=8," in sel and "z=12," in sel
    assert lines() == [f"tag {sel} add aoe2mc.own",                    # the old tag selects them: mark them first
                       "execute as @e[tag=aoe2mc.own] on vehicle run tag @s add aoe2mc.own",   # and their horses
                       "tag @e[tag=aoe2mc.own] remove aoe2mc.p1", "tag @e[tag=aoe2mc.own] add aoe2mc.p2",
                       "team join p2 @e[tag=aoe2mc.own]", "tag @e[tag=aoe2mc.own] remove aoe2mc.own"]


def test_a_gaia_source_and_the_same_player_write_no_command():
    assert lines(player=0) == lines(target=1) == []   # target 0: tests/test_trigger_ownership_gaia.py (#2908)


def ownership_scenario(path):
    """The tiny map with a timer trigger at 10 s that gives the units of player 1 in tiles 0..5 to player 2."""
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(path.with_suffix(".tiny"))))
    t = scn.trigger_manager.add_trigger("Defect")
    t.new_condition.timer(timer=10)
    t.new_effect.change_ownership(source_player=1, target_player=2, area_x1=0, area_y1=0, area_x2=5, area_y2=5)
    return scenarios.save(scn, str(path))


def test_the_effect_is_read_and_converted(tmp_path):
    src = ownership_scenario(tmp_path / "o.aoe2scenario")
    (defect,) = aoe2mc.read_scenario(src)[4]["triggers"]
    assert defect["effects"][0]["target"] == 2 and defect["effects"][0]["player"] == 1
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    fn = os.path.join(tmp_path, "W", "datapacks", "aoe2mc", "data", "aoe2mc", "function")
    with open(os.path.join(fn, "trigger", f"{defect['id']}.mcfunction")) as f:
        assert "team join p2 @e[tag=aoe2mc.own]" in f.read().splitlines()
