"""AoE2 damage and hit points of the units of the game program (#514): game/combat.py and the plugin on Paper."""
import re
import shutil
import time

import pytest

from game import combat, run


def test_damage_with_armor_and_bonus():
    assert combat.damage("MILITIA", "MILITIA") == 4                    # 4 - 0 melee armor
    assert combat.damage("SPEARMAN", "KNIGHT") == 3 - 2 + 15           # melee armor 2, bonus against cavalry
    assert combat.damage("SPEARMAN", "MILITIA") == 3                   # no bonus against infantry
    assert combat.damage("ARCHER", "KNIGHT") == 4 - 2                  # an arrow hits the pierce armor
    assert combat.damage("ARCHER", "SPEARMAN") == 4 - 0 + 3
    assert combat.damage("VILLAGER", "BATTERING_RAM") == 3 + 3          # the ram has melee armor -3
    assert combat.damage("ARCHER", "BATTERING_RAM") == 1               # at least 1
    assert combat.damage("HALBERDIER", "WAR_ELEPHANT") == 6 - 1 + 28


def test_stats_command():
    assert combat.stats_command("u-1", "MILITIA") == "aoe stats u-1 40 4 0 1 0 infantry - 24"
    assert combat.stats_command("u-2", "SPEARMAN") == "aoe stats u-2 45 3 0 0 0 infantry,spearman camel:12,cavalry:15,elephant:15 35"
    assert combat.stats_command("u-3", "ARCHER").split()[3:] == ["30", "4", "0", "0", "1", "archer", "spearman:3", "24"]

    class Game:
        sent = []

        def command(self, c):
            self.sent.append(c)
            return "Stats: 1 units"
    data = {"objects": [{"kind": "unit", "player": 1, "name": "MILITIA", "uuid": "a"},
                        {"kind": "unit", "player": 0, "name": "DEER", "uuid": "b"},       # Gaia keeps vanilla
                        {"kind": "building", "player": 1, "name": "HOUSE"}]}
    assert combat.setup(Game(), data) == 1 and Game.sent == [combat.stats_command("a", "MILITIA"), "aoe sight a 16"]


def health(game, tag):
    out = game.command(f"data get entity @e[tag={tag},limit=1] Health")
    m = re.search(r"(-?[\d.]+)f", out)
    return float(m.group(1)) if m and "has the following" in out else None


@pytest.mark.mc
def test_militia_kills_militia_in_10_hits(tiny_world, tmp_path):
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
        assert health(game, "a") == health(game, "b") == 40.0
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
        assert seen[0] == 40.0 and all(a - b == 4 for a, b in zip(seen, seen[1:])), seen   # 4 per hit
        assert seen[-1] == 4.0, seen          # the 10th hit (4 -> 0) kills it
        assert 0 < health(game, "a") < 40.0   # the target hits back without an order (#733), but dies first
