"""The towers have their AoE2 DE values and shoot arrows as the town center (#1112): combat.BUILDINGS and the plugin."""
import shutil
import time

import pytest

from game import combat, run
from test_damage import health

# AoE2 DE (wiki): hit points, attack, melee armor, pierce armor, range in tiles, reload in seconds
AOE2 = {"BOMBARD_TOWER": (2220, 120, 3, 9, 8, 6.0),
        "FORTIFIED_TOWER": (1900, 8, 4, 7, 13, 3.0),
        "GUARD_TOWER": (1500, 7, 2, 8, 8, 2.0),
        "KEEP": (2250, 8, 3, 9, 8, 2.0),
        "WATCH_TOWER": (1020, 5, 1, 7, 8, 2.0)}


@pytest.mark.parametrize("name", sorted(AOE2))
def test_each_tower_has_its_aoe2_values(name):
    s = combat.BUILDINGS[name]
    assert (s.hp, s.attack, s.melee, s.pierce, s.range, s.reload) == AOE2[name]
    assert combat.stats(name) is s and "building" in s.classes


def test_a_tower_gets_its_attack_in_the_building_command():
    uuid = "00000000-0000-0000-0000-000000000001"
    cmd, = [c for c in combat.building(uuid, "WATCH_TOWER", 1, (8, 64, 8, 11, 76, 11)) if c.startswith("aoe building")]
    assert cmd == f"aoe building {uuid} 1020 1 7 8 64 8 11 76 11 5 32 24 4 building,standard,stone"   # 8 tiles of 4 blocks, 2 s / 1.7 * 20
    cmd, = [c for c in combat.building(uuid, "BOMBARD_TOWER", 1, (8, 64, 8, 11, 76, 11)) if c.startswith("aoe building")]
    assert cmd.endswith(" 120 32 71 4 building,standard,stone")


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
        assert health(game, "e") == 40.0
        for c in combat.building(uuid, "WATCH_TOWER", 1, box):
            game.command(c)
        hp = []
        while len(hp) < 40 and (not hp or hp[-1] == 40.0):
            hp.append(health(game, "e"))
            time.sleep(0.1)
        assert hp[-1] < 40 and (40 - hp[-1]) % 4 == 0, hp                    # 4 per arrow: attack 5 - pierce armor 1
