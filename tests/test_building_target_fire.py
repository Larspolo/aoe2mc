"""The invisible target of a building does not burn (#1526): the slime of the blacksmith stood in its lava cauldron and
campfire, kept `Fire` 300, and the client drew the fire of a burning entity over the whole footprint."""
import re
import shutil
import time

import pytest

from game import combat, run


def fire(game, tag):
    out = game.command(f"data get entity @e[tag={tag},limit=1] Fire")
    m = re.search(r"(-?\d+)s", out)
    return int(m.group(1)) if m and "has the following" in out else None


@pytest.mark.mc
def test_the_target_of_a_blacksmith_does_not_burn_in_its_lava_cauldron_and_campfire(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                    # a floor in the air, inside the world border
    box = (20, y, 20, 31, y + 12, 31)          # a blacksmith of 3 x 3 tiles
    uuid = combat.target_uuid([20, 20, 32, 32])
    with run.Game(world) as game:
        game.command("forceload add 0 0 60 60")
        game.command(f"fill 0 {y - 1} 0 59 {y - 1} 59 stone_bricks")
        game.command(f"setblock 25 {y} 25 lava_cauldron")
        game.command(f"setblock 26 {y} 26 campfire[lit=true]")
        game.command("team add p1")
        for c in combat.building(uuid, "BLACKSMITH", 1, box):
            game.command(c)
        game.command(f"tag {uuid} add smith")
        assert fire(game, "smith") is not None, "the target exists"
        time.sleep(3)
        assert fire(game, "smith") <= 0, "no fire ticks on the target"
