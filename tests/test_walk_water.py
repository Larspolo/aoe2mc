"""A villager of the plugin whose path goes through water swims fast enough to come out again (#1208): in the live
replay a villager walked into the water at a shore and swam at 0.27 blocks per second for more than a minute. The order
sets the attribute water_movement_efficiency to 1 (as Depth Strider III). Paper."""
import shutil
import time

import pytest
from test_unit_ai import data

from game import ai, run

LONG = 24                                  # the walk in blocks
WET = range(8, 18)                         # the z of the water, 2 blocks deep, its surface 1 block under the ground: the
                                           # shore of samples/de-64.3 (a swimming unit floats 1.5 blocks under the bank)


@pytest.mark.mc
def test_a_villager_crosses_water_at_its_walk_speed(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 4} {z0 - 4} {x0 + 8} {z0 + LONG + 8}")
        game.command(f"fill {x0 - 3} {y - 4} {z0 - 2} {x0 + 5} {y - 1} {z0 + LONG + 2} stone_bricks")
        game.command(f"fill {x0 - 3} {y - 3} {z0 + WET[0]} {x0 + 5} {y - 2} {z0 + WET[-1]} water")
        game.command(f"fill {x0 - 3} {y - 1} {z0 + WET[0]} {x0 + 5} {y - 1} {z0 + WET[-1]} air")

        def walk(tag, z1):
            """Blocks per second of the villager `tag` from the start of the water to the bank, on its walk to z1."""
            t0, track = time.time(), []
            ai.move(game, f"@e[tag={tag},limit=1]", "VILLAGER_MALE", 4, x0 + 1.5, y, z1 + 0.5, rate=4.0)
            while time.time() < t0 + 30 and abs((p := data(game, tag, "Pos"))[2] - z1 - 0.5) > 1.5:
                track.append((time.time(), p[2]))
                time.sleep(0.05)
            a, b = z0 + WET[0], z0 + WET[-1] + 1.5
            t1 = next((t for t, z in track if z >= a), None)
            t2 = next((t for t, z in track if z >= b), time.time())
            return (b - a) / (t2 - t1) if t1 else 0.0
        # it starts in the water: a land unit does not walk into water deeper than 1 block (#1669), but swims out
        game.command(f'summon villager {x0 + 1.5} {y - 2} {z0 + WET[0] + 0.5} {{NoAI:1b,Tags:["v"]}}')
        time.sleep(1)
        wet = walk("v", z0 + LONG)
        want = ai.walk_speed("VILLAGER_MALE", 4, 4.0)
        print("wet", wet, "want", want)
        assert wet > 0.2 * want, (wet, want)              # 3.3 to 6.0; 0.8 without the attribute and the climb, 12.8 on land
