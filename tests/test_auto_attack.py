"""Idle soldiers attack the nearest enemy in their AoE2 line of sight (#775): combat.sight_command and the plugin."""
import shutil
import time

import pytest

from game import combat, run
from test_damage import health
from test_unit_ai import data


def test_sight_command():
    for name, T in (("MILITIA", 4), ("ARCHER", 4), ("LIGHT_CAVALRY", 2)):   # tiles of sight × T blocks
        assert combat.sight_command("u", name, T) == f"aoe sight u {combat.sight(name) * T}", name
    assert combat.sight_command("u", "VILLAGER", 4) is None and combat.sight_command("u", "MONK", 4) is None


@pytest.mark.mc
def test_idle_soldiers_attack_enemies_in_sight(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 60} {z0 + 80}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 56} {y - 1} {z0 + 76} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        # tag: (x, z, team, AoE2 unit). T = 4: the champion a sees b 3 tiles away (and wins); c does not see d 10 tiles
        # away; the villager v does not start a fight with w; m walks 3 tiles past n and does not stop
        units = {"a": (2, 2, "p1", "CHAMPION"), "b": (14, 2, "p2", "MILITIA"),
                 "c": (2, 22, "p1", "MILITIA"), "d": (42, 22, "p2", "MILITIA"),
                 "v": (2, 40, "p1", "VILLAGER"), "w": (6, 40, "p2", "VILLAGER"),
                 "m": (2, 60, "p1", "MILITIA"), "n": (30, 72, "p2", "MONK")}
        for tag, (dx, dz, team, name) in units.items():
            game.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + dz + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name)).strip() == "Stats: 1 units"
            cmd = combat.sight_command(f"@e[tag={tag},limit=1]", name, 4)
            assert cmd is None or game.command(cmd).strip() == "Sight: 1 units"
        goal = (x0 + 52.5, y, z0 + 60.5)
        assert game.command("aoe moveto @e[tag=m] {} {} {} 1.0".format(*goal)).strip() == "Moved 1 units"
        end = time.time() + 60
        while time.time() < end and health(game, "b") is not None:
            time.sleep(0.2)
        assert health(game, "b") is None                                  # a attacked b without an order
        full = {n: combat.stats(n).hp for n in ("MILITIA", "VILLAGER", "MONK")}
        assert health(game, "d") == full["MILITIA"] and data(game, "c", "Pos")[0] < x0 + 4   # d is out of the sight of c
        assert health(game, "w") == health(game, "v") == full["VILLAGER"]   # villagers do not start a fight
        end = time.time() + 60
        while time.time() < end and abs((data(game, "m", "Pos") or [0])[0] - goal[0]) > 1:
            time.sleep(0.5)
        p = data(game, "m", "Pos")                                        # m walked on to its goal past n
        assert health(game, "n") == full["MONK"] and p and abs(p[0] - goal[0]) < 2 and abs(p[2] - goal[2]) < 2, p
