"""Mounted units attack (#710): the rider takes the target of `aoe attack` on its horse, and the horse follows the path
of the rider (vanilla: a riding mob uses the navigation of its vehicle)."""
import math
import shutil
import time

import pytest
from test_ranged import data

from game import combat, run

KNIGHT = ('summon horse {x} {y} {z} {{NoAI:1b,Tame:1b,Tags:["k"],equipment:{{saddle:{{id:"minecraft:saddle",count:1}}}},'
          'Passengers:[{{id:"minecraft:zombie",NoAI:1b,Tags:["kr"],'
          'equipment:{{mainhand:{{id:"minecraft:iron_sword",count:1}}}}}}]}}')
ARCHER = ('summon skeleton_horse {x} {y} {z} {{NoAI:1b,Tame:1b,Tags:["c"],'
          'equipment:{{saddle:{{id:"minecraft:saddle",count:1}}}},Passengers:[{{id:"minecraft:skeleton",NoAI:1b,'
          'Tags:["cr"],equipment:{{mainhand:{{id:"minecraft:bow",count:1}}}}}}]}}')


def floor(game, x0, y, z0, length):
    game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + length + 2} {z0 + 8}")
    game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + length} {y - 1} {z0 + 6} stone_bricks")
    game.command("time set midnight")
    for t in ("p1", "p2"):
        game.command(f"team add {t}")


def hits(game, tag, start, n, seconds):
    """The health values of the entity with `tag` after each hit, until n hits or the time ends."""
    out, last, end = [], start, time.time() + seconds
    while time.time() < end and len(out) < n:
        h = (data(game, tag, "Health") or [0.0])[0]
        if h < last:
            out.append(h)
            last = h
        time.sleep(0.05)
    return out


@pytest.mark.mc
def test_mounted_units_attack(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        floor(game, x0, y, z0, 42)
        game.command(KNIGHT.format(x=x0 + 0.5, y=y, z=z0 + 2.5))
        game.command(f'summon villager {x0 + 12.5} {y} {z0 + 2.5} {{NoAI:1b,Tags:["v"]}}')
        game.command("team join p1 @e[tag=k]")
        game.command("team join p2 @e[tag=v]")
        game.command(combat.stats_command("@e[tag=k,limit=1]", "KNIGHT"))
        game.command(combat.stats_command("@e[tag=v,limit=1]", "VILLAGER"))
        assert game.command("aoe attack @e[tag=k] @e[tag=v,limit=1]").strip() == "Attack: 1 units"
        hp, d = combat.stats("VILLAGER").hp, combat.damage("KNIGHT", "VILLAGER")   # the AoE2 damage of one hit
        assert hits(game, "v", float(hp), 2, 30) == [hp - d, hp - 2 * d]
        end = time.time() + 10
        while time.time() < end and data(game, "v", "Health") is not None:
            time.sleep(0.1)
        assert data(game, "v", "Health") is None, "the villager is alive"

        game.command(ARCHER.format(x=x0 + 0.5, y=y, z=z0 + 4.5))
        game.command(f'summon zombie {x0 + 36.5} {y} {z0 + 4.5} {{NoAI:1b,IsBaby:0b,Tags:["t"]}}')
        game.command("team join p1 @e[tag=c]")
        game.command("team join p2 @e[tag=t]")
        assert game.command(combat.range_command("@e[tag=c,limit=1]", "CAVALRY_ARCHER", 4)).strip() == "Range: 1 units"
        game.command(combat.stats_command("@e[tag=c,limit=1]", "CAVALRY_ARCHER"))
        game.command("aoe stats @e[tag=t,limit=1] 1000 0 0 0 0 infantry -")    # many hit points, no armor
        assert game.command("aoe attack @e[tag=c] @e[tag=t,limit=1]").strip() == "Attack: 1 units"
        assert "aoe_range" in game.command("aoe goals @e[tag=cr,limit=1]")
        got = hits(game, "t", 1000.0, 3, 40)
        a, t = data(game, "c", "Pos"), data(game, "t", "Pos")
        d = math.hypot(a[0] - t[0], a[2] - t[2])
        assert 13 <= d <= 16.5, d             # the horse stopped at the range of 4 tiles (16 blocks)
        arrow = combat.damage("CAVALRY_ARCHER", "X", t=combat.Stats(1000, 0, 0, 0, 0, 0.0, classes=("infantry",)))
        assert len(got) == 3 and got[0] == 1000.0 - arrow, got
