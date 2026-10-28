"""A fallen building leaves no blocks also when its box has more blocks than one /fill takes (#3076): a Wonder at
--tile-size 6 has 30 x 30 x 41 = 36900 blocks, the server fills at most 32768 in one command."""
import shutil
import time

import pytest

from game import combat

BOX = (0, 100, 0, 29, 140, 29)                                      # 30 x 41 x 30 blocks


@pytest.mark.mc
def test_a_large_building_falls_with_no_blocks_left(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y0, z0, x1, y1, z1 = BOX
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x1 + 2} {z1 + 2}")
        for y in range(y0, y1 + 1, 20):                                 # 30 x 20 x 30 = 18000 blocks per fill
            assert "filled" in game.command(f"fill {x0} {y} {z0} {x1} {min(y + 19, y1)} {z1} stone").lower()
        game.command("team add p2")
        uuid = combat.target_uuid([x0, z0, x1 + 1, z1 + 1])
        for c in combat.building(uuid, "WONDER", 2, BOX, T=6):
            game.command(c)
        assert game.command(f"aoe destroy {uuid}").strip() == "Destroy: 1 buildings"
        time.sleep(2)
        for y in (y0, (y0 + y1) // 2, y1):
            for x, z in ((x0, z0), (x1, z0), (x0, z1), (x1, z1), ((x0 + x1) // 2, (z0 + z1) // 2)):
                assert "passed" not in game.command(f"execute if block {x} {y} {z} stone"), (x, y, z)
