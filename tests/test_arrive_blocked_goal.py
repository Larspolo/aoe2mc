"""A small unit that arrives near a goal block with no place to stand stays there (#1292). Its path ends on another
block (the nearest free one), and the rest of that path passed the goal: an eagle scout of the replay walked 2.06 blocks
with no order. Paper."""
import math
import shutil
import time

import pytest
from test_horse_rest import track
from test_unit_ai import data

from game import ai, run


@pytest.mark.mc
def test_a_unit_stays_where_it_arrives_near_a_blocked_goal(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 4, 180, 4                       # a floor in the air: no terrain in the way
    goal = (x0 + 0.5, z0 + 0.5)                 # a block center, as in the replay
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 8} {z0 - 8} {x0 + 8} {z0 + 16}")
        game.command(f"fill {x0 - 6} {y - 1} {z0 - 6} {x0 + 6} {y - 1} {z0 + 12} stone_bricks")
        game.command(f"fill {x0} {y} {z0} {x0} {y + 1} {z0 + 1} stone")   # the goal block and the block south of it
        game.command("time set midnight")                                  # the husk does not burn (it does not)
        game.command(f'summon husk {x0 + 0.5} {y} {z0 + 9.5} {{NoAI:1b,Tags:["e"],PersistenceRequired:1b}}')
        time.sleep(1)
        t0 = time.time()
        ai.move(game, "@e[tag=e,limit=1]", "EAGLE_SCOUT", 4, goal[0], y, goal[1], rate=4.0)
        while time.time() < t0 + 20 and math.dist(data(game, "e", "Pos")[::2], goal) > 1.5:
            time.sleep(0.02)
        arrived = data(game, "e", "Pos")
        way = track(game, "e", 2.0)
        print("arrived", arrived, "way", way, "end", data(game, "e", "Pos"))
        assert math.dist(arrived[::2], goal) <= 1.5, arrived
        assert way < 0.5, way
