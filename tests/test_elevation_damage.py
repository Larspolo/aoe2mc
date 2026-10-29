"""The AoE2 elevation rule of the damage (#2307): a hit from higher ground deals more, from lower ground less, and the
elevation bonuses of the civilizations (game/data/civs.jsonl, key "elevation"; the tests use own factors)."""
import re
import shutil
import time

import pytest

from game import civs, combat, run

H = 3                                                    # blocks of one elevation level (--level-height)
D = combat.damage("MILITIA", "MILITIA")                  # the normal damage
UP, LOW = civs.ELEVATION_BASE["up"], civs.ELEVATION_BASE["low"]


@pytest.fixture(autouse=True)
def bonuses(monkeypatch):
    """Own factors in place of the key "elevation" of game/data/civs.jsonl."""
    monkeypatch.setattr(civs, "ELEVATION", {"TATARS": {"up": 1.5}, "GEORGIANS": {"low": 0.6}, "MACEDONIANS": {"high": 0.9}})


def hit(dy, a=None, t=None, attacker="MILITIA", target="MILITIA"):
    return max(1, combat.damage(attacker, target) * combat.elevation(dy, H, a, t))


def test_a_higher_unit_deals_more_and_a_lower_one_less():
    assert hit(0) == hit(2) == hit(-2) == D              # the same level: the normal damage
    assert hit(H) == hit(3 * H) == pytest.approx(D * UP) and hit(H) > D   # also from more levels higher
    assert hit(-H) == pytest.approx(D * LOW) and hit(-H) < D
    assert hit(-H, attacker="ARCHER", target="BATTERING_RAM") >= 1   # at least 1


def test_the_up_factor_of_the_attacker():
    assert hit(H, "TATARS") == pytest.approx(D * 1.5) and hit(-H, "TATARS") == pytest.approx(D * LOW)
    assert hit(H, "BRITONS", "TATARS") == pytest.approx(D * UP)


def test_the_low_factor_of_the_target():
    assert hit(-H, "BRITONS", "GEORGIANS") == pytest.approx(D * 0.6) and hit(H, "BRITONS", "GEORGIANS") == pytest.approx(D * UP)
    assert hit(-H, "GEORGIANS", "BRITONS") == pytest.approx(D * LOW)


def test_the_high_factor_of_the_target():
    assert hit(H, "BRITONS", "MACEDONIANS") == pytest.approx(D * UP * 0.9) and hit(-H, "BRITONS", "MACEDONIANS") == pytest.approx(D * LOW)
    assert hit(H, "TATARS", "MACEDONIANS") == pytest.approx(D * 1.5 * 0.9)


def test_the_elevation_command_names_the_factors_of_each_player():
    data = {"level_height": 3, "players": {"2": {"civ": "TATARS"}, "1": {"civ": "BRITONS"}, "10": {"civ": "GEORGIANS"}}}
    assert combat.elevation_command(data) == f"aoe elevation 3 p1:{UP:g}:{LOW:g}:1 p2:1.5:{LOW:g}:1 p10:{UP:g}:0.6:1"
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
        game.command(f"fill {x0 - 1} {y + 4} {z0 - 1} {x0 + 10} {y + 4} {z0 + 10} stone_bricks")   # a roof: no sky light, no sun burn (#3212)
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
                if h is not None and h < combat.STATS["MILITIA"].hp and tag not in first:
                    first[tag] = h
            time.sleep(0.05)
        hp = combat.STATS["MILITIA"].hp                   # a from below: * 0.75, b from above: * 1.25
        assert first == {"a": pytest.approx(hp - D * 0.75), "b": pytest.approx(hp - D * 1.25)}, first
