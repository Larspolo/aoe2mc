"""AoE2 damage and hit points of the units of the game program (#514): game/combat.py and the plugin on Paper."""
import re
import shutil
import time

import pytest

from game import ai, combat, run

S = combat.Stats


def test_damage_with_armor_and_bonus():
    sword = S(40, 4, 0, 1, 0, 2.0, {}, ("infantry",))
    spear = S(45, 3, 0, 0, 0, 3.0, {"cavalry": 15}, ("infantry", "spearman"))
    bow = S(30, 4, 0, 0, 4, 2.0, {"spearman": 3}, ("archer",))
    horse = S(100, 10, 2, 2, 0, 1.8, {}, ("cavalry",))
    ram = S(175, 2, -3, 180, 0, 3.0, {}, ("siege",))
    assert combat.damage("A", "B", sword, sword) == 4                  # 4 - 0 melee armor
    assert combat.damage("A", "B", spear, horse) == 3 - 2 + 15         # melee armor 2, bonus against cavalry
    assert combat.damage("A", "B", spear, sword) == 3                  # no bonus against infantry
    assert combat.damage("A", "B", bow, horse) == 4 - 2                # an arrow hits the pierce armor
    assert combat.damage("A", "B", bow, spear) == 4 - 0 + 3
    assert combat.damage("A", "B", sword, ram) == 4 + 3                # negative melee armor adds damage
    assert combat.damage("A", "B", bow, ram) == 1                      # at least 1


def test_stats_command():
    spear = S(45, 3, 0, 0, 0, 3.0, {"cavalry": 15, "camel": 12}, ("infantry", "spearman"))
    assert combat.stats_command("u-1", "X", S(40, 4, 0, 1, 0, 2.0, {}, ("infantry",))) == \
        "aoe stats u-1 40 4 0 1 0 infantry - 24"
    assert combat.stats_command("u-2", "X", spear) == "aoe stats u-2 45 3 0 0 0 infantry,spearman camel:12,cavalry:15 35"
    assert combat.stats_command("u-3", "X", spear._replace(range=4)).split()[7] == "1"     # ranged

    class Game:
        sent = []

        def command(self, c):
            self.sent.append(c)
            return "Stats: 1 units"
    data = {"objects": [{"kind": "unit", "player": 1, "name": "MILITIA", "uuid": "a"},
                        {"kind": "unit", "player": 0, "name": "DEER", "uuid": "b"},       # Gaia keeps vanilla
                        {"kind": "building", "player": 1, "name": "HOUSE"}]}
    assert combat.setup(Game(), data) == 1 and Game.sent == [combat.stats_command("a", "MILITIA"), combat.sight_command("a", "MILITIA", 4),
                                                    ai.speed_command("a", "MILITIA", 4)]


def health(game, tag):
    out = game.command(f"data get entity @e[tag={tag},limit=1] Health")
    m = re.search(r"(-?[\d.]+)f", out)
    return float(m.group(1)) if m and "has the following" in out else None


@pytest.mark.mc
def test_militia_kills_militia_with_the_aoe2_damage(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 12} {z0 + 12}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 10} {y - 1} {z0 + 10} stone_bricks")
        game.command("time set midnight")
        game.command("difficulty hard")       # vanilla zombies hit harder on hard: the AoE2 damage must not
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        for tag, dx, team in (("a", 2, "p1"), ("b", 4, "p2")):
            game.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", "MILITIA")).strip() == "Stats: 1 units"
        game.command("item replace entity @e[tag=b] armor.chest with diamond_chestplate")   # vanilla armor: no effect
        hp, hit = float(combat.STATS["MILITIA"].hp), combat.damage("MILITIA", "MILITIA")
        assert health(game, "a") == health(game, "b") == hp
        assert game.command("aoe attack @e[tag=a] @e[tag=b,limit=1]").strip() == "Attack: 1 units"
        seen, end = [], time.time() + 60
        while time.time() < end:
            h = health(game, "b")
            if h is None:                     # dead: the entity is gone
                break
            if not seen or h != seen[-1]:
                seen.append(h)
            time.sleep(0.1)
        assert health(game, "b") is None, seen
        assert seen[0] == hp and all(a - b == hit for a, b in zip(seen, seen[1:])), seen   # the AoE2 damage per hit
        assert 0 < seen[-1] <= hit, seen      # the last hit kills it
        assert 0 < health(game, "a") < hp     # the target hits back without an order (#733), but dies first
