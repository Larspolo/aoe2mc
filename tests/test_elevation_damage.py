"""The AoE2 elevation rule of the damage (#2307): a hit from higher ground deals more, from lower ground less, and the
elevation bonuses of the Tatars, Georgians and Macedonians (game/civs.jsonl, key "elevation")."""
import re
import shutil
import time

import pytest

from game import combat, run

H = 3                                                    # blocks of one elevation level (--level-height)


def hit(dy, a=None, t=None, attacker="MILITIA", target="MILITIA"):
    return max(1, combat.damage(attacker, target) * combat.elevation(dy, H, a, t))


def test_a_higher_unit_deals_more_and_a_lower_one_less():
    assert hit(0) == hit(2) == hit(-2) == 4              # the same level: the normal damage
    assert hit(H) == hit(3 * H) == 5                     # +25 %, also from more levels higher
    assert hit(-H) == 3                                  # -25 %
    assert hit(-H, attacker="ARCHER", target="BATTERING_RAM") == 1   # at least 1


def test_tatars_deal_50_percent_more_from_higher_ground():
    assert hit(H, "TATARS") == 6 and hit(-H, "TATARS") == 3
    assert hit(H, "BRITONS", "TATARS") == 5


def test_georgians_take_40_percent_less_from_lower_ground():
    assert hit(-H, "BRITONS", "GEORGIANS") == pytest.approx(2.4) and hit(H, "BRITONS", "GEORGIANS") == 5
    assert hit(-H, "GEORGIANS", "BRITONS") == 3


def test_macedonians_take_10_percent_less_from_higher_ground():
    assert hit(H, "BRITONS", "MACEDONIANS") == pytest.approx(4.5) and hit(-H, "BRITONS", "MACEDONIANS") == 3
    assert hit(H, "TATARS", "MACEDONIANS") == pytest.approx(5.4)


def test_the_elevation_command_names_the_factors_of_each_player():
    data = {"level_height": 3, "players": {"2": {"civ": "TATARS"}, "1": {"civ": "BRITONS"}, "10": {"civ": "GEORGIANS"}}}
    assert combat.elevation_command(data) == "aoe elevation 3 p1:1.25:0.75:1 p2:1.5:0.75:1 p10:1.25:0.6:1"
    assert combat.elevation_command({"players": {}}) is None


def health(game, tag):
    out = game.command(f"data get entity @e[tag={tag},limit=1] Health")
    m = re.search(r"(-?[\d.]+)f", out)
    return float(m.group(1)) if m and "has the following" in out else None


@pytest.mark.mc
def test_a_militia_on_a_step_hits_harder_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                                # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 12} {z0 + 12}")
        game.command("time set midnight")                 # a zombie in the sun burns: 1 damage on a (#2965)
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 10} {y - 1} {z0 + 10} stone_bricks")
        game.command(f"fill {x0 + 2} {y} {z0 + 2} {x0 + 2} {y} {z0 + 2} stone_bricks")   # a pillar for unit a
        game.command(f"fill {x0 + 3} {y + 2} {z0 + 1} {x0 + 6} {y + 2} {z0 + 3} glass")   # b cannot jump onto it
        assert game.command("aoe elevation 1 p1:1.25:0.75:1").strip() == "Elevation: 1 blocks, 1 teams"
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        for tag, dx, dy, team in (("a", 2, 1, "p1"), ("b", 3, 0, "p2")):
            game.command(f'summon zombie {x0 + dx + 0.5} {y + dy} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", "MILITIA")).strip() == "Stats: 1 units"
        game.command("aoe stance @e[tag=a] stand_ground")   # a hits back from its pillar
        assert game.command("aoe attack @e[tag=b] @e[tag=a,limit=1]").strip() == "Attack: 1 units"
        first, end = {}, time.time() + 60                 # the first hits: later the units walk off the step
        while time.time() < end and len(first) < 2:
            for tag in "ab":
                h = health(game, tag)
                if h is not None and h < 40 and tag not in first:
                    first[tag] = h
            time.sleep(0.05)
        assert first == {"a": 40 - 3, "b": 40 - 5}, first  # a from below: 4 * 0.75, b from above: 4 * 1.25
