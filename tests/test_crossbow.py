"""A skeleton unit with a crossbow shoots in the game program (#633): the vanilla skeleton shot accepts only a bow."""
import shutil
import time

import pytest
from test_ranged import data

from game import combat, run


@pytest.mark.mc
def test_arbalester_shoots_with_a_crossbow(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 8}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 28} {y - 1} {z0 + 6} stone_bricks")
        game.command("time set midnight")
        game.command("difficulty hard")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon skeleton {x0 + 0.5} {y} {z0 + 2.5} {{NoAI:1b,Tags:["a"],'
                     'equipment:{mainhand:{id:"minecraft:crossbow",count:1}}}')
        game.command(f'summon zombie {x0 + 24.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["t"]}}')
        game.command("team join p1 @e[tag=a]")
        game.command("team join p2 @e[tag=t]")
        assert game.command(combat.range_command("@e[tag=a,limit=1]", "ARBALESTER", 4)).strip() == "Range: 1 units"
        game.command(combat.stats_command("@e[tag=a,limit=1]", "ARBALESTER"))
        game.command("aoe stats @e[tag=t,limit=1] 1000 0 0 0 0 infantry -")
        assert game.command("aoe attack @e[tag=a] @e[tag=t,limit=1]").strip() == "Attack: 1 units"
        hits = 2 * combat.damage("ARBALESTER", "MILITIA", t=combat.Stats(1000, 0, 0, 0, 0, 0, {}, ("infantry",))) + 1
        start, end = 1000.0, time.time() + 40
        while time.time() < end and (data(game, "t", "Health") or [start])[0] > start - hits:
            time.sleep(0.2)
        health = (data(game, "t", "Health") or [start])[0]
        hand = game.command("data get entity @e[tag=a,limit=1] equipment.mainhand.id")
        log = "\n".join(game.server.log)
    assert "Entity threw exception" not in log
    assert health <= start - hits, health     # several arrows hit: the unit stayed and shot again
    assert "minecraft:crossbow" in hand, hand
