"""The Paper plugin (#1168): units that stood without AI on one cell do not fly away at their next order. A mob without
AI does not move, but the pushes of the other units on its place add to its velocity; `unit()` clears it."""
import os
import re
import shutil
import time

import pytest
from test_plugin import pos

from game import run

PLUGIN = os.path.join(os.path.dirname(__file__), "..", "game", "plugin", "src", "main", "java", "aoe2mc", "AoePlugin.java")


def test_an_order_clears_the_velocity_of_a_unit_without_ai():
    with open(PLUGIN) as f:
        src = f.read()
    body = src[src.index("private Mob unit(Entity e)"):]
    body = body[:body.index("\n    }\n")]
    assert re.search(r"if \(!mob\.hasAI\(\)\) \{\s*mob\.setAI\(true\);.*?mob\.setVelocity\(new Vector\(0, mob\.getVelocity\(\)"
                     r"\.getY\(\), 0\)\);", body, re.S), body


@pytest.mark.mc
def test_villagers_on_one_cell_walk_and_do_not_fly(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 20, 200, 20                   # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 40} {z0 - 40} {x0 + 40} {z0 + 40}")
        game.command(f"fill {x0 - 40} {y - 1} {z0 - 40} {x0 + 40} {y - 1} {z0 + 40} stone_bricks")
        for k in range(8):                    # as in de-64.3 at 6:29: 8 villagers of a group on one cell
            game.command(f"summon villager {x0 + 0.4 + k % 3 * 0.1} {y} {z0 + 0.4 + k // 3 * 0.1} "
                         f"{{NoAI:1b,Tags:[\"u\",\"u{k}\"]}}")
        time.sleep(10)                        # the pushes add up while they have no AI
        start = [pos(game, f"u{k}") for k in range(8)]
        assert game.command(f"aoe moveto @e[tag=u] {x0 - 5.5} {y} {z0 + 0.5}").strip() == "Moved 8 units"
        time.sleep(0.5)
        end = [pos(game, f"u{k}") for k in range(8)]
        far = [max(abs(p[0] - s[0]), abs(p[2] - s[2])) for s, p in zip(start, end)]
        assert max(far) < 8, far              # a walk of 0.5 s (and the reads); without the fix: 10 to 40 blocks
        assert all(p[0] <= s[0] + 1 for s, p in zip(start, end)), (start, end)   # none goes away from the goal
