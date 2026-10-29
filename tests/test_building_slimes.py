"""The target slimes of buildings stay alive in their walls (#3723): the plugin cancels damage that does not come from
an entity also for a tagged slime with no `aoe building` entry, and a dead target does not split into small slimes."""
import os
import re
import shutil
import time

import pytest

from game import combat, run


def count(game):
    out = game.command("execute if entity @e[type=slime,tag=aoe2mc.building]")
    return int(re.search(r"(?i)count: (\d+)", out).group(1)) if "Count" in out else 0


@pytest.mark.mc
def test_building_slimes_do_not_suffocate_in_their_walls(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200
    box = (20, y, 20, 27, y + 6, 27)                       # a house of 2 x 2 tiles
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command("team add p1")
        game.command(f"fill 18 {y - 1} 18 50 {y + 8} 50 stone")          # the slimes stand in solid blocks
        for c in combat.building(combat.target_uuid([20, 20, 28, 28]), "HOUSE", 1, box):
            game.command(c)
        game.command(f'summon slime 44 {y} 44 {{Size:3,NoAI:1b,NoGravity:1b,PersistenceRequired:1b,'
                     f'Tags:["aoe2mc.building"]}}')                     # a target with no entry
        time.sleep(10)
        assert count(game) == 2
        with open(os.path.join(game.folder, "logs", "latest.log")) as f:
            assert "suffocated" not in f.read()
