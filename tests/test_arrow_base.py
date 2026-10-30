"""The AoE2 DE base number of arrows of a building (#1201): an empty town center shoots none ("only when garrisoned by
Villagers, archer units" on the AoE2 wiki). Each garrisoned villager or foot archer adds 1 (#1113)."""
import shutil
import time

import pytest
from test_damage import health

from game import combat, garrison, run

UUID = "00000000-0000-0000-0000-000000000001"
BOX = (8, 64, 8, 23, 104, 23)


def test_each_villager_or_foot_archer_inside_adds_an_arrow():
    for name in ("TOWN_CENTER", "CASTLE", "WATCH_TOWER"):
        base = garrison.arrows(name, [])
        assert garrison.arrows(name, ["VILLAGER_MALE"] * 3) == base + 3 and garrison.arrows(name, ["ARCHER"]) == base + 1


def test_building_command_sends_the_arrows_of_the_units_inside():
    assert f"aoe arrows {UUID} {garrison.arrows('TOWN_CENTER', [])}" in combat.building(UUID, "TOWN_CENTER", 1, BOX)
    inside = ["VILLAGER", "CROSSBOWMAN"]
    assert f"aoe arrows {UUID} {garrison.arrows('CASTLE', inside)}" in combat.building(UUID, "CASTLE", 1, BOX, inside=inside)
    assert not any(c.startswith("aoe arrows") for c in combat.building(UUID, "HOUSE", 1, BOX))   # no attack


class Game:
    def __init__(self):
        self.sent = []

    def command(self, cmd):
        self.sent.append(cmd)
        return "Stats: 1 units"


def test_setup_counts_the_start_garrison():
    data = {"objects": [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "ref": 5, "footprint": [0, 0, 16, 16]},
                        {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "ref": 6, "uuid": "u6", "holder": 5},
                        {"kind": "unit", "name": "ARCHER", "player": 1, "ref": 7, "uuid": "u7", "holder": 5},
                        {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "ref": 8, "uuid": "u8"}]}
    game = Game()
    combat.setup(game, data)
    assert [c for c in game.sent if c.startswith("aoe arrows")] == \
        [f"aoe arrows {combat.target_uuid([0, 0, 16, 16])} {garrison.arrows('TOWN_CENTER', ['VILLAGER_MALE', 'ARCHER'])}"]


@pytest.mark.mc
def test_empty_town_center_does_not_shoot(tiny_world, tmp_path):
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
        game.command("time set midnight")      # zombies burn in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon zombie 48.5 {y} 28.5 {{NoAI:1b,IsBaby:0b,Tags:["e"]}}')   # 12 blocks from the edge
        game.command("team join p2 @e[tag=e]")
        game.command("aoe stats @e[tag=e,limit=1] 1000 4 0 1 0 infantry - 20")
        for c in combat.building(uuid, "TOWN_CENTER", 1, box):
            game.command(c)
        time.sleep(5)
        assert health(game, "e") == 1000.0                                  # no arrow
        game.command(f"aoe arrows {uuid} {garrison.arrows('TOWN_CENTER', ['VILLAGER'])}")
        for _ in range(40):
            if health(game, "e") < 1000:
                break
            time.sleep(0.1)
        assert health(game, "e") == 1000 - (combat.stats("TOWN_CENTER").attack - 1)   # 1 arrow: attack - pierce 1
