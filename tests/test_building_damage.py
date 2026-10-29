"""Military units damage an enemy building in the game program (#517): game/combat.py building and the plugin."""
import re
import shutil
import time

import pytest

from game import combat, run


def test_pierce_damage_on_a_building_is_small():
    assert 1 <= combat.damage("ARCHER", "HOUSE") < combat.damage("CHAMPION", "HOUSE")   # at least 1
    assert combat.damage("CROSSBOWMAN", "BARRACKS") >= 1
    assert combat.damage("BATTERING_RAM", "HOUSE") > combat.stats("BATTERING_RAM").attack   # the ram bonus against buildings


def test_building_commands():
    uuid = combat.target_uuid([8, 8, 16, 16])
    assert uuid == combat.target_uuid([8, 8, 16, 16]) != combat.target_uuid([8, 8, 16, 17])
    summon, team, aoe = combat.building(uuid, "HOUSE", 2, (8, 64, 8, 15, 104, 15))
    assert summon.startswith("summon slime 12.0 64 12.0 {Size:15,NoAI:1b") and combat.INVISIBLE in summon
    assert 15 * combat.SLIME > 7 and team == f"team join p2 {uuid}"   # the slime covers the 8 blocks
    s = combat.stats("HOUSE")
    assert aoe == f"aoe building {uuid} {s.hp} {s.melee} {s.pierce} 8 64 8 15 104 15"
    ints = [int(i) for i in re.search(r"UUID:\[I;([-\d,]+)\]", summon).group(1).split(",")]
    assert "".join(f"{i & 0xFFFFFFFF:08x}" for i in ints) == uuid.replace("-", "")


def test_setup_makes_targets_for_the_buildings_of_the_players():
    class Game:
        sent = []

        def command(self, c):
            self.sent.append(c)
            return "Stats: 1 units"
    ground = [" ".join(["64"] * 12) for _ in range(12)]
    ground[2] = " ".join(["63"] + ["64"] * 11)                         # the lowest ground next to the house
    data = {"ground": ground, "objects": [
        {"kind": "building", "player": 2, "name": "HOUSE", "footprint": [1, 1, 3, 3]},
        {"kind": "building", "player": 0, "name": "HOUSE", "footprint": [5, 5, 7, 7]},         # Gaia: none
        {"kind": "building", "player": 1, "name": "FARM", "footprint": [8, 8, 11, 11]}]}      # no hit points
    assert combat.setup(Game(), data) == 0
    s = combat.stats("HOUSE")
    assert len(Game.sent) == 4 and Game.sent[2].endswith(f" {s.hp} {s.melee} {s.pierce} 1 63 1 2 103 2")
    assert Game.sent[3] == f"aoe label {combat.target_uuid([1, 1, 3, 3])} House"


def hp(game, uuid):
    m = re.search(r"has (-?\d+) ", game.command(f"scoreboard players get {uuid} aoe_hp"))
    return int(m.group(1)) if m else None


@pytest.mark.mc
def test_two_soldiers_destroy_a_house(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, box = 200, (8, 200, 8, 13, 240, 13)                             # a house in the air, inside the world border
    with run.Game(world) as game:
        game.command("forceload add -2 -2 24 24")
        game.command(f"fill 0 {y - 1} 0 21 {y - 1} 21 stone_bricks")
        game.command(f"fill 8 {y} 8 13 {y + 3} 13 oak_planks")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        uuid = combat.target_uuid([8, 8, 14, 14])
        for c in combat.building(uuid, "HOUSE", 2, box):
            game.command(c)
        full, hit = combat.stats("HOUSE").hp, combat.damage("CHAMPION", "HOUSE")
        assert hp(game, uuid) == full
        for tag, x in (("a", 4.5), ("b", 17.5)):
            game.command(f'summon zombie {x} {y} 10.5 {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join p1 @e[tag={tag}]")
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", "CHAMPION")).strip() == "Stats: 1 units"
        assert game.command(f"aoe attack @e[tag=a] {uuid}").strip() == "Attack: 1 units"
        assert game.command(f"aoe attack @e[tag=b] {uuid}").strip() == "Attack: 1 units"
        seen, end = [full], time.time() + 120
        while time.time() < end and (h := hp(game, uuid)) is not None:
            if h != seen[-1]:
                seen.append(h)
            time.sleep(0.1)
        assert hp(game, uuid) is None, seen                            # 0: the plugin removed the score
        assert all((a - b) % hit == 0 for a, b in zip(seen, seen[1:])) and len(seen) > 5, seen   # whole hits
        assert "Test failed" in game.command(f"execute if entity {uuid}")          # the target is gone
        for x, dy, z in ((10, 1, 10), (8, 0, 8), (13, 3, 13)):               # the house blocks are gone
            assert "Test passed" in game.command(f"execute if block {x} {y + dy} {z} air"), (x, dy, z)
        assert "Test passed" in game.command(f"execute if block 10 {y - 1} 10 stone_bricks")   # the floor stays
