"""The Paper plugin (#811): a villager whose walk order finds no path stands still (NoAI), as after a walk that
arrives, and the server log names the dropped order."""
import os
import re
import shutil
import time

import pytest
from test_plugin import pos

from game import run


@pytest.mark.mc
def test_a_villager_without_a_path_stands_still(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # two closed cells in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 12} {z0 + 12}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 1} {y + 2} {z0 + 1} stone hollow")    # the start cell
        game.command(f"fill {x0 + 7} {y - 1} {z0 + 7} {x0 + 11} {y + 3} {z0 + 11} stone hollow")  # the goal box
        game.command(f"summon villager {x0 + 0.5} {y} {z0 + 0.5} {{NoAI:1b,Tags:[\"u\"]}}")
        start = pos(game, "u")
        assert start

        def still():                          # NoAI 1b; a mob with AI has no NoAI tag ("Found no elements")
            return game.command("data get entity @e[tag=u,limit=1] NoAI").strip().endswith("1b")
        assert game.command(f"aoe moveto @e[tag=u] {x0 + 9.5} {y} {z0 + 9.5}").strip() == "Moved 1 units"
        time.sleep(1)
        assert not still()                    # it tries to walk
        time.sleep(9)
        assert still()
        p = pos(game, "u")
        assert max(abs(p[0] - start[0]), abs(p[2] - start[2])) <= 1, (start, p)
        with open(os.path.join(game.folder, "logs", "latest.log")) as f:
            log = f.read()
        assert re.search(rf"aoe2mc: no path \S+ {x0 + 9.5} {y}\.0 {z0 + 9.5}", log), log[-2000:]
