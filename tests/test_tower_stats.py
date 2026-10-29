"""The towers shoot arrows as the town center (#1112): the values of combat.BUILDINGS in the plugin command."""
import shutil
import time

import pytest

from game import combat, run
from test_damage import health

def test_a_tower_gets_its_attack_in_the_building_command():
    uuid = "00000000-0000-0000-0000-000000000001"
    for name in ("WATCH_TOWER", "BOMBARD_TOWER"):
        s = combat.stats(name)
        cmd, = [c for c in combat.building(uuid, name, 1, (8, 64, 8, 11, 76, 11)) if c.startswith("aoe building")]
        assert cmd.startswith(f"aoe building {uuid} {s.hp} {s.melee} {s.pierce} 8 64 8 11 76 11 "), name
        assert cmd.split()[12:15] == [str(s.attack), str(s.range * 4), str(round(s.reload / combat.NORMAL * 20))], name   # tiles of 4 blocks, ticks


@pytest.mark.mc
def test_watch_tower_shoots_the_enemy_in_range(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                    # a floor in the air, inside the world border
    box = (20, y, 20, 23, y + 12, 23)          # a watch tower of 1 x 1 tile
    uuid = combat.target_uuid([20, 20, 24, 24])
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command("time set midnight")      # zombies burn in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon zombie 36.5 {y} 21.5 {{NoAI:1b,IsBaby:0b,Tags:["e"]}}')   # 12 blocks from the edge
        game.command("team join p2 @e[tag=e]")
        assert game.command(combat.stats_command("@e[tag=e,limit=1]", "MILITIA")).strip() == "Stats: 1 units"
        full = combat.stats("MILITIA").hp
        assert health(game, "e") == full
        for c in combat.building(uuid, "WATCH_TOWER", 1, box):
            game.command(c)
        hp = []
        while len(hp) < 40 and (not hp or hp[-1] == full):
            hp.append(health(game, "e"))
            time.sleep(0.1)
        arrow = combat.stats("WATCH_TOWER").attack - combat.stats("MILITIA").pierce
        assert hp[-1] < full and (full - hp[-1]) % arrow == 0, hp           # per arrow: attack - pierce armor
