"""The towers, the castle and the dock do not shoot at a unit inside their AoE2 minimum range (#1546): the last
number of the attack part of `aoe building`, and the arrow loop of the plugin (the key "min_range" of
data/buildings.jsonl, combat.FORT_MIN_RANGE)."""
import shutil
import time

import pytest

from game import combat, run
from test_damage import health

UUID = "00000000-0000-0000-0000-000000000001"


def attack(name, T=4):
    """The attack, range, reload and minimum range of the `aoe building` command of building `name`."""
    cmd, = [c for c in combat.building(UUID, name, 1, (8, 64, 8, 11, 76, 11), T) if c.startswith("aoe building")]
    return cmd.split()[12:16]


@pytest.mark.parametrize("name", ["BOMBARD_TOWER", "CASTLE", "GUARD_TOWER", "KEEP", "WATCH_TOWER"])
def test_each_tower_and_the_castle_send_their_minimum_range_in_blocks(name):
    low = combat.FORT_MIN_RANGE[name]
    assert float(attack(name, T=4)[3]) == low * 4 and float(attack(name, T=2)[3]) == low * 2


def test_the_town_center_sends_its_minimum_range_too():
    assert float(attack("TOWN_CENTER")[3]) == combat.FORT_MIN_RANGE.get("TOWN_CENTER", 0) * 4


@pytest.mark.mc
def test_a_watch_tower_does_not_shoot_at_an_enemy_next_to_its_wall(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                    # a floor in the air, inside the world border
    box = (20, y, 20, 23, y + 12, 23)          # a watch tower of 1 x 1 tile (T = 4): range 32, minimum range 4 blocks
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command("time set midnight")      # zombies burn in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        # n: an enemy 1.5 blocks south of the wall, inside the minimum range; e: an enemy 5 tiles (20 blocks) east of
        # the wall, not on the line of the arrows to n
        for tag, x, z in (("n", 21.5, 25.5), ("e", 44.5, 21.5)):
            game.command(f'summon zombie {x} {y} {z} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join p2 @e[tag={tag}]")
            game.command(f"aoe stats @e[tag={tag},limit=1] 1000 4 0 1 0 infantry - 20")
        for c in combat.building(combat.target_uuid([20, 20, 24, 24]), "WATCH_TOWER", 1, box):
            game.command(c)
        end = time.time() + 15
        while health(game, "e") == 1000.0:
            assert time.time() < end, "the tower did not shoot at the enemy at 5 tiles"
            time.sleep(0.2)
        time.sleep(3)
        assert health(game, "n") == 1000.0, "the tower shot at the enemy inside its minimum range"
        assert health(game, "e") < 1000.0
