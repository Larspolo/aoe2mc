"""A dead siege unit or War Wagon leaves nothing on the map (#3017): its minecart, its carrier and its cart go too."""
import shutil
import time

import pytest
from test_siege_walk import summon

from game import ai, combat, run


def gone(game, selector):
    return "passed" not in game.command(f"execute if entity {selector}")


@pytest.mark.mc
def test_a_dead_siege_unit_leaves_no_minecart(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 10} {z0 + 10}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 8} {y - 1} {z0 + 8} stone_bricks")
        assert "Summoned" in summon(game, "MANGONEL", x0 + 2.5, y, z0 + 2.5, "mg")
        sel = "@e[type=minecart,tag=mg]"
        assert game.command(ai.speed_command(sel, "MANGONEL", 4)).strip() == "Speed: 1 units"   # makes the carrier
        assert game.command(f"aoe stats {sel} 175 2 0 180 0 - -").strip() == "Stats: 1 units"
        assert "passed" in game.command("execute if entity @e[tag=aoe2mc.carrier]")
        game.command(f"execute as {sel} on passengers run kill @s")                       # the crew dies
        time.sleep(2)
        assert gone(game, sel), "the minecart is alive"
        assert gone(game, "@e[tag=aoe2mc.carrier]"), "the carrier is alive"
        assert gone(game, "@e[type=item,distance=..20,nbt={Item:{id:\"minecraft:minecart\"}}]"), "a minecart item"


@pytest.mark.mc
def test_a_dead_war_wagon_leaves_no_cart(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 10} {z0 + 10}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 8} {y - 1} {z0 + 8} stone_bricks")
        assert "Summoned" in summon(game, "WAR_WAGON", x0 + 2.5, y, z0 + 2.5, "ww")
        horse = "@e[type=horse,tag=ww,limit=1]"
        assert game.command(combat.stats_command(horse, "WAR_WAGON")).strip() == "Stats: 1 units"
        assert "Count: 1" in game.command("execute if entity @e[type=item_display]")    # the cart of the wagon
        game.command(f"kill {horse}")
        time.sleep(2)
        assert gone(game, "@e[type=horse,tag=ww]"), "the horse is alive"
        assert gone(game, "@e[type=item_display]"), "the cart stays"
