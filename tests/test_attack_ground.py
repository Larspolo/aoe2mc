"""aoe attackground: a siege unit shoots at a point until a new order (#4078)."""
import shutil
import time

import pytest

from game import ai, combat, run
from test_ranged import data
from test_siege_walk import summon


@pytest.mark.mc
def test_a_mangonel_shoots_at_the_ground_until_stop(tiny_world, tmp_path):
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
        game.command(f"team join p1 {o}")
        assert game.command(combat.stats_command(o, "MANGONEL")).strip() == "Stats: 1 units"
        assert game.command(combat.range_command(o, "MANGONEL", 4)).strip() == "Range: 1 units"
        game.command(ai.speed_command(o, "MANGONEL", 4))
        assert game.command(f"aoe attackground {o} {x0 + 20.5} {y} {z0 + 4.5}").strip() == "Attack ground: 1 units"
        time.sleep(3)                         # it shoots at the empty point; then an enemy steps onto it
        game.command(f'summon zombie {x0 + 20.5} {y} {z0 + 4.5} {{NoAI:1b,IsBaby:0b,Tags:["m1"]}}')
        game.command("team join p2 @e[tag=m1]")
        game.command("aoe stats @e[tag=m1,limit=1] 1000 4 0 1 0 infantry -")   # militia values, many hit points
        end = time.time() + 20
        while time.time() < end and (data(game, "m1", "Health") or [1000.0])[0] == 1000.0:
            time.sleep(0.2)
        assert (data(game, "m1", "Health") or [1000.0])[0] < 1000.0     # the blast at the point hits it
        assert game.command(f"aoe stop {o}").strip() == "Stopped 1 units"
        time.sleep(0.5)
        hp = data(game, "m1", "Health")[0]
        time.sleep(8)                                                   # more than 2 reloads
        assert data(game, "m1", "Health")[0] == hp                      # no more shots
