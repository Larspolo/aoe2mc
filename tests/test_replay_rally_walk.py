"""A unit that walks down a slope at an angle (a trained unit on its rally walk) stays at the end of its walk: it does
not walk back to the path points that steer() took it past (#2303: a spearman of de-64.3 arrived and then walked 25
blocks back up the hill). Paper."""
import math
import shutil
import time

import pytest
from test_unit_ai import data

from game import ai, run

STEPS, SIDE = 24, 10                       # down 1 block per block toward +z, and SIDE blocks to the side (+x)


@pytest.mark.mc
def test_a_unit_stays_at_the_end_of_its_walk_down_a_slope(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # the top of the slope in the air, inside the world border
    goal = (x0 + SIDE + 1.5, z0 + STEPS + 2.5)  # a block center on the flat rows at the bottom, as in the replay
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 4} {z0 - 4} {x0 + SIDE + 6} {z0 + STEPS + 10}")
        for k in range(STEPS + 6):                                    # 3 flat rows at each end
            top = y - 1 - min(max(k - 3, 0), STEPS)
            game.command(f"fill {x0 - 2} {top - 1} {z0 + k} {x0 + SIDE + 4} {top} {z0 + k} stone_bricks")
        game.command("time set midnight")
        game.command(f'summon husk {x0 + 0.5} {y} {z0 + 0.5} {{NoAI:1b,Tags:["s"]}}')
        time.sleep(1)
        t0 = time.time()
        ai.move(game, "@e[tag=s,limit=1]", "SPEARMAN", 4, goal[0], y - STEPS, goal[1], rate=4.0)
        while time.time() < t0 + 20 and math.dist(data(game, "s", "Pos")[::2], goal) > 1.5:
            time.sleep(0.02)
        far = 0.0
        for _ in range(40):                                           # 2 s with no order
            far = max(far, math.dist(data(game, "s", "Pos")[::2], goal))
            time.sleep(0.05)
        print("arrived after", time.time() - t0 - 2, "s, then at most", far, "blocks from the goal")
        assert far <= 2, far
