"""A hit on the crew of a siege unit keeps the crew in its minecart with NoAI (#3016): the attack back must not turn on
the brain of the crew (a warden digs, a breeze shoots, a piglin attacks by itself)."""
import shutil
import time

import pytest
from test_damage import health
from test_stances_kinds import enemy, summon

from game import combat, run

T = 4
Y = 200


def crew_no_ai(game, tag):
    out = game.command(f"execute as @e[type=minecart,tag={tag}r,limit=1] on passengers run data get entity @s NoAI")
    return "1b" in out


def siege(game, name, pos, tag, sight=False):
    assert "Summoned" in summon(game, name, pos, tag), name
    game.command(f"team join p1 @e[tag={tag}]")
    sel = f"@e[tag={tag}r,limit=1]"
    assert game.command(combat.stats_command(sel, name)).strip() == "Stats: 1 units", name
    for cmd in (combat.range_command(sel, name, T), sight and combat.sight_command(sel, name, T)):
        if cmd:
            game.command(cmd)
    assert crew_no_ai(game, tag), name


def arena(game, x0, z0):
    game.command("time set midnight")                          # the zombies do not burn
    for t in ("p1", "p2"):
        game.command(f"team add {t}")
    game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 10}")
    game.command(f"fill {x0 - 1} {Y - 1} {z0 - 1} {x0 + 28} {Y - 1} {z0 + 8} stone_bricks")


def hit(game, tag, by):
    game.command(f"damage @e[tag={tag},tag=!{tag}r,limit=1] 1 minecraft:mob_attack by @e[tag={by},limit=1]")


@pytest.mark.mc
def test_a_hit_trebuchet_keeps_its_crew_still(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, z0 = 1, 1
    with run.Game(world) as game:
        arena(game, x0, z0)
        siege(game, "TREBUCHET", (x0 + 2.5, Y, z0 + 2.5), "tb")
        enemy(game, (x0 + 4.5, Y, z0 + 2.5), "tm")
        hit(game, "tb", "tm")
        end = time.time() + 10
        while time.time() < end:
            assert crew_no_ai(game, "tb")              # in the minecart (a passenger) and NoAI 1b
            time.sleep(1)


@pytest.mark.mc
def test_a_hit_scorpion_shoots_back_with_a_still_crew(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, z0 = 1, 1
    with run.Game(world) as game:
        arena(game, x0, z0)
        siege(game, "SCORPION", (x0 + 2.5, Y, z0 + 2.5), "sc", sight=True)
        enemy(game, (x0 + 18.5, Y, z0 + 2.5), "se")    # 16 blocks: in the range of 7 tiles
        hit(game, "sc", "se")
        end = time.time() + 5
        while time.time() < end and (health(game, "se") or 1000) >= 1000:
            assert crew_no_ai(game, "sc")
            time.sleep(0.5)
        assert (health(game, "se") or 1000) < 1000
        assert crew_no_ai(game, "sc")
