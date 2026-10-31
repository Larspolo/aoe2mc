"""An "Objects in Area" trigger counts only the units of the type in its condition (#681)."""
import os

import pytest
from test_trigger_area import area, score, wait_score

import aoe2mc
from tools import scenarios


def test_units_have_a_type_tag():
    o = dict(kind="U", name="KNIGHT", id=38, player=1, x=1.5, y=1.5)
    nbt = aoe2mc.units.make_entity(o, {}, (6.0, 65.0, 6.0), aoe2mc.np.random.default_rng(1))
    assert [str(t) for t in aoe2mc.units.top_entity(nbt)["Tags"]] == ["aoe2mc.p1", "aoe2mc.t38"]


def test_type_filter_in_the_selector():
    t = area(1, [(1, 1, [0, 0, 0, 0])])
    t["conditions"][0]["object"] = 38
    tick = aoe2mc.trigger_files([t], T=4)[1]["data/aoe2mc/function/tick.mcfunction"]
    assert tick.startswith("execute if entity @e[tag=aoe2mc.p1,tag=!aoe2mc.mount,tag=aoe2mc.t38,x=0,y=-64,z=0,dx=3,")


def test_class_or_group_filter_skips_the_trigger():
    for key in ("class", "group"):
        t = area(1, [(1, 1, [0, 0, 0, 0])])
        t["conditions"][0][key] = 6
        assert aoe2mc.trigger_files([t]) == ([], {})


@pytest.mark.mc
def test_knight_fires_the_trigger_and_the_villager_not(tmp_path):
    from test_paper import paper_reachable

    from game import run
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    src = scenarios.triggers(str(tmp_path / "t.aoe2scenario"))
    world = str(tmp_path / "W")
    aoe2mc.convert(src, world)
    with run.Game(world) as game:
        game.forceload()
        game.command("tp @e[tag=aoe2mc.p1,type=villager,limit=1] 20 70 20")
        assert wait_score(game, 1, 3) is None                          # a villager: not the type of the condition
        game.command("execute as @e[tag=aoe2mc.t38] on vehicle run tp @s 16 70 16")   # the horse with its rider
        game.command("tp @e[tag=aoe2mc.t38] 16 70 16")                 # a knight without horse
        assert wait_score(game, 1) == 1, game.command("data get entity @e[tag=aoe2mc.t38,limit=1] Pos")
        assert score(game) == 1
    assert os.path.isdir(world)
