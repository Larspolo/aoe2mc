"""A building shoots at the next enemy when it cannot shoot its nearest one (#1328): the check #1204 saw a town center
that shot no arrow at all, because an enemy stood in its passage with no free cell next to it."""
import shutil
import time

import pytest

from game import combat, run
from test_damage import health


@pytest.mark.mc
def test_town_center_shoots_the_next_enemy_when_the_nearest_has_no_free_side(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                    # a floor in the air, inside the world border
    box = (20, y, 20, 35, y + 40, 35)          # a town center of 4 x 4 tiles
    uuid = combat.target_uuid([20, 20, 36, 36])
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command(f"fill 22 {y} 22 24 {y + 2} 24 stone_bricks hollow")     # a cell under the building, closed
        game.command(f"setblock 23 {y} 23 air")
        game.command(f"setblock 23 {y + 1} 23 air")
        game.command("time set midnight")      # zombies burn in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon zombie 23.5 {y} 23.5 {{NoAI:1b,IsBaby:0b,Tags:["e","near"]}}')   # no free side
        game.command(f'summon zombie 28.5 {y} 48.5 {{NoAI:1b,IsBaby:0b,Tags:["e","far"]}}')    # 12 blocks south
        game.command("team join p2 @e[tag=e]")
        for tag in ("near", "far"):
            game.command(f"aoe stats @e[tag={tag},limit=1] 1000 4 0 1 0 infantry - 20")
        for c in combat.building(uuid, "TOWN_CENTER", 1, box, inside=["VILLAGER"] * 3):
            game.command(c)
        h = health(game, "far")
        time.sleep(6)
        arrow = combat.stats("TOWN_CENTER").attack - 1                 # attack - pierce armor 1
        assert health(game, "far") < h - 2 * arrow, "3 arrows about each 1.2 s at the enemy with a free way"
