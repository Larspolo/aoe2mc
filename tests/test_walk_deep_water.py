"""A land unit of the plugin stops at the shore of water deeper than 1 block when no land path goes around it (without
the fix it walks on the floor of the water), but walks through the 1-block shallows (#1669: militia of the bot walked
into a lake). Paper."""
import shutil
import time

import pytest
from test_siege_walk import summon
from test_unit_ai import data

from game import ai, run

LAKE = range(15, 18)                       # the x of a lake 2 blocks deep (a shore of a map) across the first floor
SHALLOW = range(40, 51)                    # the z of a second floor: 1-block shallows across all of it, no way around


@pytest.mark.mc
def test_a_land_unit_stops_at_deep_water_and_walks_through_the_shallows(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 40} {z0 + 52}")
        game.command(f"fill {x0} {y - 4} {z0} {x0 + 34} {y - 1} {z0 + 30} stone_bricks")
        game.command(f"fill {x0} {y - 4} {z0 + SHALLOW[0]} {x0 + 34} {y - 1} {z0 + SHALLOW[-1]} stone_bricks")
        game.command(f"fill {x0 + LAKE[0]} {y - 3} {z0} {x0 + LAKE[-1]} {y - 2} {z0 + 30} water")
        game.command(f"fill {x0 + LAKE[0]} {y - 1} {z0} {x0 + LAKE[-1]} {y - 1} {z0 + 30} air")   # a shore of a map
        game.command(f"fill {x0 + LAKE[0]} {y - 1} {z0 + SHALLOW[0]} {x0 + LAKE[-1]} {y - 1} {z0 + SHALLOW[-1]} water")
        tracks = {}
        for tag, z in (("a", z0 + 1.5), ("b", z0 + 45.5)):
            assert "Summoned" in summon(game, "MILITIA", x0 + 3.5, y, z, tag)
            ai.move(game, f"@e[tag={tag},limit=1]", "MILITIA", 4, x0 + 30.5, y, z)
            tracks[tag] = z, []
        end = time.time() + 25
        while time.time() < end:
            for tag, (_, track) in tracks.items():
                if p := data(game, tag, "Pos"):
                    track.append(p)
            time.sleep(0.1)
    a, b = tracks["a"][1], tracks["b"][1]
    assert a and max(p[0] for p in a) < x0 + LAKE[0] + 0.3 and min(p[1] for p in a) >= y - 0.1, a[-1]   # the shore
    assert a[-1][0] > x0 + LAKE[0] - 3, a[-1]                       # it walked up to the shore
    assert abs(b[-1][0] - x0 - 30.5) < 1.5, b[-1]                   # through the shallows
    assert any(x0 + LAKE[0] <= p[0] < x0 + LAKE[-1] + 1 for p in b)
