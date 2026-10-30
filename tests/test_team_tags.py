"""Units of one player without a team yet do not attack each other (#986): the plugin takes the side of a unit from
its tag aoe2mc.pN until the pulse of the datapack puts it in its team."""
import shutil
import time

import pytest
from test_damage import health

from game import combat, run


@pytest.mark.mc
def test_units_without_a_team_attack_only_enemies(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 40}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 26} {y - 1} {z0 + 36} stone_bricks")
        game.command("time set midnight")
        # tag: (x, z, player tag, AoE2 unit), no team: a and b of player 1 stand side by side; c sees d of player 2
        units = {"a": (2, 2, "aoe2mc.p1", "LONG_SWORDSMAN"), "b": (4, 2, "aoe2mc.p1", "ARCHER"),
                 "c": (2, 30, "aoe2mc.p1", "CHAMPION"), "d": (12, 30, "aoe2mc.p2", "MILITIA")}
        for tag, (dx, dz, side, name) in units.items():
            mob = "skeleton" if name == "ARCHER" else "zombie"
            game.command(f'summon {mob} {x0 + dx + 0.5} {y} {z0 + dz + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}","{side}"]}}')
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name)).strip() == "Stats: 1 units"
            assert game.command(combat.sight_command(f"@e[tag={tag},limit=1]", name, 4)).strip() == "Sight: 1 units"
        full = {t: health(game, t) for t in "ab"}
        end = time.time() + 60
        while time.time() < end and health(game, "d") is not None:
            time.sleep(0.2)
        assert health(game, "d") is None                  # c attacked the enemy d
        assert {t: health(game, t) for t in "ab"} == full  # a and b did not fight
