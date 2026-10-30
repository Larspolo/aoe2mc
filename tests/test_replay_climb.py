"""A scout cavalry (a horse, 2 x 2 blocks) walks up and down a slope at an angle at its walk speed: its path goes in
L steps there, and the plugin steers it along the line (#1022). Paper."""
import math
import shutil
import time

import pytest
from test_unit_ai import data

from game import ai, run

STEPS, SIDE = 32, 12                       # up 1 block per block toward z, and SIDE blocks to the side (x); a walk of
# about 2 s: the start of the order is a small part of the time (#1713)


@pytest.mark.mc
def test_a_scout_cavalry_climbs_a_slope_at_an_angle(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 180, 1                     # the bottom of the slope in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 4} {z0 - 4} {x0 + SIDE + 6} {z0 + STEPS + 10}")
        for k in range(STEPS + 7):                                    # 3 flat rows at each end
            top = y - 1 + min(max(k - 3, 0), STEPS)
            game.command(f"fill {x0 - 2} {top - 1} {z0 + k} {x0 + SIDE + 4} {top} {z0 + k} stone_bricks")
        game.command("time set midnight")                              # the rider does not burn
        game.command(f'summon horse {x0 + 1} {y} {z0 + 1} {{NoAI:1b,Tame:1b,Tags:["h"],'
                     f'Passengers:[{{id:"minecraft:zombie",NoAI:1b}}]}}')
        time.sleep(1)

        def walk(x1, z1):
            """Blocks per second (straight line, no height) of the horse from its place to (x1, z1)."""
            p0 = data(game, "h", "Pos")
            t0 = time.time()
            ai.move(game, "@e[tag=h,limit=1]", "SCOUT_CAVALRY", 4, x1, y + (z1 > z0 + 3) * STEPS, z1, rate=4.0)
            while time.time() < t0 + 20 and math.dist((p := data(game, "h", "Pos"))[::2], (x1, z1)) > 1.6:
                time.sleep(0.05)
            return math.dist(p[::2], p0[::2]) / (time.time() - t0)
        up = walk(x0 + 1 + SIDE, z0 + STEPS + 5)
        down = walk(x0 + 1, z0 + 1)
        want = ai.walk_speed("SCOUT_CAVALRY", 4, 4.0)                 # 19.2 blocks per second
        print("up", up, "down", down, "want", want)
        assert up > 0.8 * want, (up, want)
        assert down > 0.6 * want, (down, want)
