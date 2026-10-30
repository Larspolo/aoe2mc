"""Units attack back when an enemy hits them, as with the AoE2 default stance (#733): the plugin on Paper."""
import shutil
import time

import pytest
from test_damage import health
from test_unit_ai import data

from game import combat, run


@pytest.mark.mc
def test_units_attack_back_without_an_order(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 40} {z0 + 40}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 36} {y - 1} {z0 + 36} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        # tag: (x, z, team, AoE2 unit); three pairs 12 blocks apart: a fights b, c hits a walking d, e hits villager v
        units = {"a": (2, 2, "p1", "MILITIA"), "b": (4, 2, "p2", "MILITIA"),
                 "c": (2, 14, "p1", "MILITIA"), "d": (4, 14, "p2", "MILITIA"),
                 "e": (2, 26, "p1", "MILITIA"), "v": (4, 26, "p2", "VILLAGER")}
        for tag, (dx, dz, team, name) in units.items():
            game.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + dz + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name)).strip() == "Stats: 1 units"
        goal = (x0 + 24.5, y, z0 + 14.5)
        assert game.command("aoe moveto @e[tag=d] {} {} {} 1.0".format(*goal)).strip() == "Moved 1 units"
        assert game.command("aoe attack @e[tag=a] @e[tag=b,limit=1]").strip() == "Attack: 1 units"
        for a, t in (("c", "d"), ("e", "v")):                           # one hit, as from a unit
            game.command(f"damage @e[tag={t},limit=1] 1 minecraft:mob_attack by @e[tag={a},limit=1]")
        hp, dmg = combat.stats("MILITIA").hp, combat.damage                # the AoE2 damage of a militia
        assert health(game, "d") == hp - dmg("MILITIA", "MILITIA")
        assert health(game, "v") == combat.stats("VILLAGER").hp - dmg("MILITIA", "VILLAGER")
        end = time.time() + 60
        while time.time() < end and health(game, "b") is not None:
            time.sleep(0.2)
        assert health(game, "b") is None                                  # a killed b ...
        assert health(game, "a") is not None and health(game, "a") < hp   # ... and b hit back before it died
        p = data(game, "d", "Pos")                                        # d walked on to its goal
        assert p and abs(p[0] - goal[0]) < 2 and abs(p[2] - goal[2]) < 2, p
        assert health(game, "c") == hp
        assert health(game, "e") == hp and data(game, "v", "Pos")[0] < x0 + 5   # the villager did not attack back
