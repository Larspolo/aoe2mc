"""Triggers stop and allow again the choice of the units of a player in an area as targets (#2826): the entity tag
aoe2mc.NO_TARGET. The game program (AoePlugin calm) chooses no tagged unit; an attack order still hits it."""
import shutil
import time

import numpy as np
import pytest

import aoe2mc
from game import combat, run
from test_damage import health


def effect(type, area=(1, 2, 2, 3), player=1):
    return dict(type=type, message="", player=player, time=0, object=None, tile=[-1, -1], area=list(area))


def lines(effects, T=4):
    trig = dict(id=8, name="t", enabled=True, looping=False, effects=effects,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], T, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/8.mcfunction", "").splitlines()


def test_disable_tags_the_units_in_the_area_and_enable_removes_the_tag():
    sel = aoe2mc.unit_selector(effect(0), 4)
    assert lines([effect(aoe2mc.DISABLE_UNIT_TARGETING)]) == [f"tag {sel} add {aoe2mc.NO_TARGET}"]
    assert lines([effect(aoe2mc.ENABLE_UNIT_TARGETING)]) == [f"tag {sel} remove {aoe2mc.NO_TARGET}"]


def test_gaia_units_and_no_area():
    assert "tag=aoe2mc.p0," in lines([effect(aoe2mc.DISABLE_UNIT_TARGETING, player=0)])[0]   # #2916
    assert lines([effect(aoe2mc.DISABLE_UNIT_TARGETING, area=(-1, -1, -1, -1))]) == []


@pytest.mark.mc
def test_a_soldier_skips_a_tagged_enemy_and_attacks_it_on_an_order(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 30}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 26} {y - 1} {z0 + 26} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        # the champion a sees the militia b 3 tiles away (T = 4): b has the tag, so a does not attack it
        for tag, (dx, team, name) in {"a": (2, "p1", "CHAMPION"), "b": (14, "p2", "MILITIA")}.items():
            game.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name)).strip() == "Stats: 1 units"
        game.command(f"tag @e[tag=b] add {aoe2mc.NO_TARGET}")
        assert game.command(combat.sight_command("@e[tag=a,limit=1]", "CHAMPION", 4)).strip() == "Sight: 1 units"
        hp = health(game, "b")
        time.sleep(5)
        assert health(game, "b") == hp                                    # no automatic attack on a tagged unit
        game.command(f"tag @e[tag=b] remove {aoe2mc.NO_TARGET}")         # "Enable Unit Targeting"
        end = time.time() + 60
        while time.time() < end and health(game, "b") is not None:
            time.sleep(0.2)
        assert health(game, "b") is None                                  # without the tag a attacks it by itself
