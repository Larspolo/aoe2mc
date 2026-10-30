"""A unit of the plugin walks down a slope without walking back and at its walk speed, with no fall damage (#888), and
up steps with a carpet (#851). Paper."""
import shutil
import time

import pytest
from test_unit_ai import data

from game import ai, run

STEPS = 24                                 # a slope of one block down per block, as the hill of samples/de-64.3


@pytest.mark.mc
def test_a_scout_walks_down_and_up_a_slope(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # the top of the slope in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 8} {z0 + STEPS + 8}")
        game.command("time set midnight")                              # husks do not burn, but no fire anyway
        for k in range(STEPS + 4):
            top = y - 1 - min(k, STEPS)
            game.command(f"fill {x0 - 1} {top - 1} {z0 + k} {x0 + 3} {top} {z0 + k} stone_bricks")
            if k % 2:                                                  # a step of 1.0625 blocks (#851)
                game.command(f"fill {x0 - 1} {top + 1} {z0 + k} {x0 + 3} {top + 1} {z0 + k} moss_carpet")

        def walk(tag, z1):
            """Blocks per second of the husk `tag` from its place to z1 on the slope."""
            t0, p0 = time.time(), data(game, tag, "Pos")
            ai.move(game, f"@e[tag={tag},limit=1]", "EAGLE_SCOUT", 4, x0 + 1.5, y - (z1 - z0), z1 + 0.5, rate=4.0)
            while time.time() < t0 + 20 and abs((p := data(game, tag, "Pos"))[2] - z1 - 0.5) > 1:
                time.sleep(0.05)
            return abs(p[2] - p0[2]) / (time.time() - t0)
        game.command(f'summon husk {x0 + 1.5} {y} {z0 + 0.5} {{NoAI:1b,Tags:["s"]}}')
        time.sleep(1)
        down = walk("s", z0 + STEPS)
        health = data(game, "s", "Health")
        up = walk("s", z0)
        want = ai.walk_speed("EAGLE_SCOUT", 4, 4.0)                   # 17.6 blocks per second
        print("down", down, "up", up, "health", health)
        assert down > 0.6 * want, (down, want)                       # 6.0 before the glide, 2.8 when it walked back
        assert health == [20.0]                                       # the glide does not end in fall damage
        assert up > 0.6 * want, (up, want)                           # 12 to 14; it stood still at a carpet step
