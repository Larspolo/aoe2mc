"""A ranged unit in a fight keeps shooting after `aoe range` (#3011): train.research() sends it after each technology
to the units whose range is not the base range, and the plugin adds the goal aoe_range again with the new range."""
import shutil
import time

import pytest
from test_ranged import data
from test_siege_walk import summon

from game import ai, combat, run

X0, Y, Z0 = 1, 200, 1                         # a floor in the air, inside the world border


def arena(game):
    game.command(f"forceload add {X0 - 2} {Z0 - 2} {X0 + 44} {Z0 + 8}")
    game.command(f"fill {X0 - 1} {Y - 1} {Z0 - 1} {X0 + 42} {Y - 1} {Z0 + 6} stone_bricks")
    game.command("time set midnight")
    game.command("difficulty hard")           # a skeleton aims better on hard: fewer misses
    for t in ("p1", "p2"):
        game.command(f"team add {t}")


def target(game, x):
    game.command(f'summon zombie {X0 + x} {Y} {Z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["t"]}}')
    game.command("team join p2 @e[tag=t]")
    game.command("aoe stats @e[tag=t,limit=1] 1000 0 0 0 0 infantry -")        # many hit points


def hits(game, n, seconds):
    """The number of hits on the target (a lower Health), up to n, in the next seconds."""
    found, last, end = 0, (data(game, "t", "Health") or [1000.0])[0], time.time() + seconds
    while time.time() < end and found < n:
        h = (data(game, "t", "Health") or [last])[0]
        if h < last:
            found, last = found + 1, h
        time.sleep(0.05)
    return found


def start(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    return shutil.copytree(tiny_world[0], tmp_path / "W")


@pytest.mark.mc
def test_an_archer_keeps_shooting_after_a_new_range(tiny_world, tmp_path):
    with run.Game(start(tiny_world, tmp_path)) as game:
        arena(game)
        game.command(f'summon skeleton {X0 + 0.5} {Y} {Z0 + 2.5} {{NoAI:1b,Tags:["a"],'
                     'equipment:{mainhand:{id:"minecraft:bow",count:1}}}')
        game.command("team join p1 @e[tag=a]")
        target(game, 20.5)
        a = "@e[tag=a,limit=1]"
        game.command(combat.range_command(a, "ARCHER", 4))
        game.command(combat.stats_command(a, "ARCHER"))
        assert game.command(f"aoe attack {a} @e[tag=t,limit=1]").strip() == "Attack: 1 units"
        assert hits(game, 2, 30) == 2
        assert game.command(combat.range_command(a, "ARCHER", 4)).strip() == "Range: 1 units"   # train.research()
        assert "aoe_range" in game.command(f"aoe goals {a}")
        assert hits(game, 2, 6) == 2                                        # it still shoots


@pytest.mark.mc
def test_a_scorpion_keeps_shooting_after_a_new_range(tiny_world, tmp_path):
    with run.Game(start(tiny_world, tmp_path)) as game:
        arena(game)
        assert "Summoned" in summon(game, "SCORPION", X0 + 1.5, Y, Z0 + 2.5, "s")
        s = "@e[type=minecart,tag=s,limit=1]"
        game.command(f"team join p1 {s}")
        target(game, 17.5)                                                   # 16 blocks: out of the minimum range
        game.command(combat.stats_command(s, "SCORPION"))
        game.command(combat.range_command(s, "SCORPION", 4))
        game.command(ai.speed_command(s, "SCORPION", 4))
        assert game.command(f"aoe attack {s} @e[tag=t,limit=1]").strip() == "Attack: 1 units"
        assert hits(game, 1, 30) == 1
        assert game.command(combat.range_command(s, "SCORPION", 4)).strip() == "Range: 1 units"
        assert hits(game, 1, 10) == 1                                       # the carrier still shoots


@pytest.mark.mc
def test_a_new_range_keeps_a_unit_with_no_ai_still(tiny_world, tmp_path):
    with run.Game(start(tiny_world, tmp_path)) as game:
        arena(game)
        game.command(f'summon skeleton {X0 + 0.5} {Y} {Z0 + 2.5} {{NoAI:1b,Tags:["a"],'
                     'equipment:{mainhand:{id:"minecraft:bow",count:1}}}')
        game.command(combat.range_command("@e[tag=a,limit=1]", "ARCHER", 4))
        assert game.command("data get entity @e[tag=a,limit=1] NoAI").strip().endswith(": 1b")   # the next order turns it on
        assert "aoe_range" not in game.command("aoe goals @e[tag=a,limit=1]")
