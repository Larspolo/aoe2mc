"""The arrows of a town center fly over the own buildings (#3562): a militia that attacks a house next to the town
center, on the far side of the house, dies, as in AoE2."""
import shutil
import time

import pytest
from test_damage import health

from game import combat, run


@pytest.mark.mc
def test_town_center_kills_a_militia_behind_a_house(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                    # a floor in the air, inside the world border
    tc, house = (20, y, 20, 35, y + 11, 35), (46, y, 24, 53, y + 7, 31)   # 4 x 4 and 2 x 2 tiles, 2 tiles apart
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command("time set midnight")      # zombies burn in the sun
        for x0, y0, z0, x1, y1, z1 in (tc, house):
            game.command(f"fill {x0} {y0} {z0} {x1} {y1} {z1} oak_planks")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        # the militia stands next to the far side of the house: 18.5 blocks (4.6 tiles) from the edge of the town center
        game.command(f'summon zombie 54.5 {y} 27.5 {{IsBaby:0b,Tags:["e"]}}')
        game.command("team join p2 @e[tag=e]")
        assert game.command(combat.stats_command("@e[tag=e,limit=1]", "MILITIA")).strip() == "Stats: 1 units"
        hut = combat.target_uuid([46, 24, 54, 32])
        for c in combat.building(hut, "HOUSE", 1, house):
            game.command(c)
        game.command(f"aoe attack @e[tag=e,limit=1] {hut}")
        for c in combat.building(combat.target_uuid([20, 20, 36, 36]), "TOWN_CENTER", 1, tc, inside=["VILLAGER"] * 5):
            game.command(c)
        hp = []
        for _ in range(60):                    # 30 s; 5 arrows of 4 damage per 1.2 s kill the 40 hit points in 3 s
            hp.append(health(game, "e"))
            if hp[-1] is None:
                break
            time.sleep(0.5)
        assert hp[-1] is None, hp
