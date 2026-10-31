"""A scout cavalry (a horse, 2 x 2 blocks) walks down a slope at an angle at its walk speed, stops at its goal and
takes no fall damage (#1078). Paper.
The speed is in server ticks from the first step to the goal (#2591): before its first step a unit stands 2 to 3 ticks
(the first AI tick, the path search), and in wall clock time a short walk measured 87 to 92 % of the speed."""
import math
import shutil
import time

import pytest
from test_unit_ai import data

from game import ai, run

STEPS, SIDE = 32, 12                       # down 1 block per block toward -z, and SIDE blocks to the side (-x)


def tick(game):
    """The game time of the server in ticks: a busy machine does not change it."""
    return int(game.command("time query gametime").split()[-2])


@pytest.mark.mc
def test_a_scout_cavalry_walks_down_a_slope_at_its_speed(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 180, 1                     # the bottom of the slope in the air, inside the world border
    x1, z1 = x0 + 1 + SIDE, z0 + STEPS + 5     # the top, on the flat rows
    goal = (x0 + 1.5, z0 + 1.5)                # a block center, as in the replay
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 4} {z0 - 4} {x0 + SIDE + 6} {z0 + STEPS + 10}")
        for k in range(STEPS + 7):                                    # 3 flat rows at each end
            top = y - 1 + min(max(k - 3, 0), STEPS)
            game.command(f"fill {x0 - 2} {top - 1} {z0 + k} {x0 + SIDE + 4} {top} {z0 + k} stone_bricks")
        game.command("time set midnight")                              # the rider does not burn
        game.command(f'summon horse {x1} {y + STEPS} {z1} {{NoAI:1b,Tame:1b,Tags:["h"],'
                     f'Passengers:[{{id:"minecraft:zombie",NoAI:1b}}]}}')
        time.sleep(1)
        health = data(game, "h", "Health")
        p0 = data(game, "h", "Pos")
        t0, first = time.time(), None
        ai.move(game, "@e[tag=h,limit=1]", "SCOUT_CAVALRY", 4, goal[0], y, goal[1], rate=4.0)
        while time.time() < t0 + 20 and math.dist((p := data(game, "h", "Pos"))[::2], goal) > 1.5:
            if first is None and p != p0:
                first = p, tick(game)
        down = math.dist(p[::2], first[0][::2]) / ((tick(game) - first[1]) / 20)
        time.sleep(1)
        end = math.dist(data(game, "h", "Pos")[::2], goal)
        want = ai.walk_speed("SCOUT_CAVALRY", 4, 4.0)                 # 19.2 blocks per second
        print("down", down, "want", want, "end", end)
        assert down > 0.9 * want, (down, want)
        assert end <= 1.5, end
        assert data(game, "h", "Health") == health
