"""An eagle scout (a husk, 1 x 1 block) walks up and down a slope at an angle at its walk speed: its path goes in
L steps there, and the plugin steers it along the line, as a horse (#851, #1022). Paper."""
import math
import shutil
import time

import pytest
from test_unit_ai import data

from game import ai, run

STEPS, SIDE = 16, 6                        # up 1 block per block toward z, and SIDE blocks to the side (x)


@pytest.mark.mc
def test_an_eagle_scout_climbs_a_slope_at_an_angle(tiny_world, tmp_path):
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
        game.command(f'summon husk {x0 + 0.5} {y} {z0 + 0.5} {{NoAI:1b,Tags:["h"]}}')
        time.sleep(1)

        def walk(x1, z1):
            """Blocks per second (straight line, no height) of the husk from its place to (x1, z1)."""
            p0 = data(game, "h", "Pos")
            t0 = time.time()
            ai.move(game, "@e[tag=h,limit=1]", "EAGLE_SCOUT", 4, x1, y + (z1 > z0 + 3) * STEPS, z1, rate=4.0)
            while time.time() < t0 + 20 and math.dist((p := data(game, "h", "Pos"))[::2], (x1, z1)) > 1.6:
                time.sleep(0.05)
            return math.dist(p[::2], p0[::2]) / (time.time() - t0)
        up = walk(x0 + 0.5 + SIDE, z0 + STEPS + 5.5)
        down = walk(x0 + 0.5, z0 + 0.5)
        want = ai.walk_speed("EAGLE_SCOUT", 4, 4.0)                   # 17.6 blocks per second
        print("up", up, "down", down, "want", want)
        assert up > 0.8 * want, (up, want)
        assert down > 0.6 * want, (down, want)
