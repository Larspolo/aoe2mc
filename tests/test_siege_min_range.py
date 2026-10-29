"""A siege unit does not shoot at a target inside its AoE2 minimum range (#1350): the last number of `aoe range`."""
import shutil
import time

import pytest

from game import ai, combat, run
from test_ranged import data
from test_siege_walk import summon


@pytest.mark.parametrize("name", sorted(combat.MIN_RANGE))
def test_the_range_command_gives_the_minimum_range_in_blocks(name):
    t = combat.range_command("u", name, 4).split()
    assert len(t) == 7 + (name in combat.PASS) and float(t[6]) == combat.MIN_RANGE[name] * 4
    assert float(t[3]) == combat.stats(name).range * 4                  # the range stays


def test_no_minimum_range_for_an_archer_and_a_ram():
    assert len(combat.range_command("u", "ARCHER", 4).split()) == 5
    assert len(combat.range_command("u", "BATTERING_RAM", 4).split()) == 6   # the melee reach, no minimum (#1399)


@pytest.mark.mc
def test_a_mangonel_does_not_hurt_an_enemy_at_1_tile_and_hurts_it_at_5_tiles(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 16}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 26} {y - 1} {z0 + 12} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        assert "Summoned" in summon(game, "MANGONEL", x0 + 1.5, y, z0 + 4.5, "o")
        o = "@e[type=minecart,tag=o,limit=1]"
        for tag, x in (("near", 5.5), ("far", 21.5)):          # 1 tile (4 blocks) and 5 tiles (20 blocks) away
            game.command(f'summon zombie {x0 + x} {y} {z0 + 4.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join p2 @e[tag={tag}]")
            game.command(f"aoe stats @e[tag={tag},limit=1] 1000 4 0 1 0 infantry -")
        game.command(f"team join p1 {o}")
        assert game.command(combat.stats_command(o, "MANGONEL")).strip() == "Stats: 1 units"
        assert game.command(combat.range_command(o, "MANGONEL", 4)).strip() == "Range: 1 units"
        game.command(ai.speed_command(o, "MANGONEL", 4))
        assert game.command(f"aoe attack {o} @e[tag=near,limit=1]").strip() == "Attack: 1 units"
        time.sleep(12)                                           # about 3 reloads of 6 AoE2 s at Normal speed
        assert data(game, "near", "Health")[0] == 1000.0, "a shot inside the minimum range"
        assert game.command(f"aoe attack {o} @e[tag=far,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 20
        while time.time() < end and data(game, "far", "Health")[0] == 1000.0:
            time.sleep(0.2)
        assert data(game, "far", "Health")[0] < 1000.0, "no shot at 5 tiles"
        assert data(game, "near", "Health")[0] == 1000.0           # the blast of 1 tile does not reach it
