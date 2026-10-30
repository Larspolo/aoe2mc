"""The Hussite Wagon shields the units behind it (#4507, AoE2 DE wiki "Hussite Wagon": "Halves the damage dealt by enemy
projectiles passing through its hitbox by taking 1 damage"): the key "shield", combat.shield_command and `aoe shield` of
the plugin. Test data, and arrows on a server."""
import re
import shutil
import time

import pytest

from game import combat, run


def test_the_shield_command_gives_the_part_and_the_damage_of_the_wagon(monkeypatch):
    monkeypatch.setattr(combat, "SHIELD", {"TEST_WAGON": {"part": 0.25, "takes": 2}})
    assert combat.shield_command("u-1", "TEST_WAGON") == "aoe shield u-1 0.25 2"
    assert combat.shield_command("u-1", "ARCHER") is None


def health(game, tag):
    out = game.command(f"data get entity @e[tag={tag},limit=1] Health")
    return float(re.findall(r"-?\d+\.?\d*", out.split(":", 1)[-1])[0])


@pytest.mark.mc
def test_an_arrow_through_the_wagon_hurts_its_target_less_and_the_wagon_by_one(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200
    with run.Game(world) as game:
        game.command("forceload add 0 0 16 16")
        game.command(f"fill 0 {y - 1} 0 15 {y - 1} 15 stone_bricks")
        game.command("time set midnight")                 # a zombie burns in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon skeleton 14.5 {y} 14.5 {{NoAI:1b,Tags:["a"]}}')
        game.command(f'summon zombie 8.5 {y} 8.5 {{NoAI:1b,IsBaby:0b,Tags:["w"]}}')
        game.command(f'summon zombie 2.5 {y} 2.5 {{NoAI:1b,IsBaby:0b,Tags:["t"]}}')
        game.command("team join p1 @e[tag=a]")
        game.command("team join p2 @e[tag=w]")
        game.command("team join p2 @e[tag=t]")
        game.command(combat.stats_command("@e[tag=a,limit=1]", "ARCHER"))
        for t in ("w", "t"):
            game.command(f"aoe stats @e[tag={t},limit=1] 1000 0 0 0 0 infantry -")
        assert game.command("aoe shield @e[tag=w,limit=1] 0.5 1").strip() == "Shield: 1 units"
        game.command("aoe attack @e[tag=a,limit=1] @e[tag=t,limit=1]")
        out = game.command("data get entity @e[tag=a,limit=1] UUID")
        owner = ",".join(re.findall(r"-?\d+", out.split(":", 1)[-1]))

        def arrow(x, z):                                   # an arrow of the archer falls on the unit at x, z
            game.command(f"summon arrow {x} {y + 2.5} {z} {{Motion:[0d,-1.5d,0d],Owner:[I;{owner}]}}")
            time.sleep(1.0)

        arrow(2.5, 2.5)                                    # straight on the target: the full damage
        full = 1000 - health(game, "t")
        arrow(8.5, 8.5)                                    # on the wagon, on the way to the target
        half = 1000 - full - health(game, "t")
        assert health(game, "w") == 999, health(game, "w")
        assert 0 < half < full, (half, full)
