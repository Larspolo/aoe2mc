"""A scout cavalry (a tamed horse with a NoAI rider) stands still after it arrives at the foot of a slope (#1132). #1078
saw it move 0.27 blocks forward and back each tick there; on main (and on the plugin of #1129) it moves 0 blocks.
Paper."""
import math
import shutil
import time

import pytest
from test_unit_ai import data

from game import ai, run

STEPS, SIDE = 16, 6                        # down 1 block per block toward -z, and SIDE blocks to the side (-x)


def track(game, tag, seconds=1.0):
    """The way of the entity with tag in seconds: the sum of the horizontal steps between samples each 0.02 s."""
    end, way, last = time.time() + seconds, 0.0, data(game, tag, "Pos")
    while time.time() < end:
        time.sleep(0.02)
        p = data(game, tag, "Pos")
        way += math.dist(p[::2], last[::2])
        last = p
    return way


@pytest.mark.mc
def test_a_scout_cavalry_stands_still_after_it_arrives(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 180, 1                     # the bottom of the slope in the air (tests/test_replay_descent.py)
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
        t0 = time.time()
        ai.move(game, "@e[tag=h,limit=1]", "SCOUT_CAVALRY", 4, goal[0], y, goal[1], rate=4.0)
        while time.time() < t0 + 20 and math.dist(data(game, "h", "Pos")[::2], goal) > 1.5:
            time.sleep(0.02)
        time.sleep(0.5)                                                # the slide of the brake
        way = track(game, "h")
        end = math.dist(data(game, "h", "Pos")[::2], goal)
        print("way", way, "end", end, "motion", data(game, "h", "Motion"))
        assert end <= 1.5, end
        assert way < 0.05, way
