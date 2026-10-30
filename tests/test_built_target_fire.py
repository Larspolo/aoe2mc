"""The target slime of a building burns not even before the "aoe building" command registers it (#4690): the slime of
a blacksmith that a player builds (build.target) touches the lava cauldron of the forge at its summon."""
import shutil
import time

import pytest
from test_building_target_fire import fire

from game import combat, run


@pytest.mark.mc
def test_a_target_slime_in_lava_does_not_burn_before_its_registration(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200
    box = (20, y, 20, 31, y + 12, 31)
    uuid = combat.target_uuid([20, 20, 32, 32])
    summon = [c for c in combat.building(uuid, "BLACKSMITH", 1, box) if c.startswith("summon ")]
    with run.Game(world) as game:
        game.command("forceload add 0 0 60 60")
        game.command(f"fill 0 {y - 1} 0 59 {y - 1} 59 stone_bricks")
        game.command(f"setblock 25 {y} 25 lava_cauldron")
        game.command(summon[0])                # only the summon: no "aoe building"
        game.command(f"tag {uuid} add smith")
        time.sleep(3)
        assert fire(game, "smith") <= 0, "no fire ticks on the target"
