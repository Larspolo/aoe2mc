"""The AoE2 stance "defensive" (#1105): a unit chases an enemy only a short way and walks back to its place."""
import math
import shutil
import time

import pytest
from test_damage import health
from test_unit_ai import data

from game import combat, run


@pytest.mark.mc
def test_defensive_unit_comes_back(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 64} {z0 + 40}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 62} {y - 1} {z0 + 38} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        # tag: (x, z, team). The militia d (defensive) and a (aggressive) each see an enemy in their lane; the lanes
        # are more than a sight of 16 blocks apart. The enemies have many hit points and no attack.
        units = {"d": (2, 2, "p1"), "e": (8, 2, "p2"), "a": (2, 34, "p1"), "f": (8, 34, "p2")}
        for tag, (dx, dz, team) in units.items():
            game.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + dz + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            sel = f"@e[tag={tag},limit=1]"
            if team == "p1":
                assert game.command(combat.stats_command(sel, "MILITIA")).strip() == "Stats: 1 units"
                game.command(combat.sight_command(sel, "MILITIA", 4))
            else:
                game.command(f"aoe stats {sel} 1000 0 0 0 0 infantry -")
        assert game.command(combat.stance_command("@e[tag=d,limit=1]", "defensive")).strip() == "Stance: 1 units"
        start = {u: data(game, u, "Pos") for u in "da"}
        end = time.time() + 15
        while time.time() < end and max(health(game, u) or 1000 for u in "ef") >= 1000:
            time.sleep(0.2)
        assert health(game, "e") < 1000 and health(game, "f") < 1000        # both attack the enemy in their sight
        for u, dz in (("e", 2), ("f", 34)):                                   # the enemies walk away, 50 blocks
            game.command(f"aoe moveto @e[tag={u}] {x0 + 58.5} {y} {z0 + dz + 0.5}")
        far = {u: 0.0 for u in "da"}
        end = time.time() + 30
        while time.time() < end:
            for u in "da":
                p = data(game, u, "Pos")
                far[u] = max(far[u], math.hypot(p[0] - start[u][0], p[2] - start[u][2]))
            time.sleep(0.5)
        p = {u: data(game, u, "Pos") for u in "da"}
        dist = {u: math.hypot(p[u][0] - start[u][0], p[u][2] - start[u][2]) for u in "da"}
        assert 10 < far["d"] < 20, far                  # d followed e to the chase distance (2 + 12 blocks) ...
        assert dist["d"] < 2, (start["d"], p["d"])      # ... and is back at its place
        assert dist["a"] > 30, (start["a"], p["a"])     # a did not come back
