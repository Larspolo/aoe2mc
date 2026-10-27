"""The line of sight of the units and buildings of one player in the live replay (#1300)."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import replay  # noqa: E402

# AoE2 DE wiki infobox "LOS" (MediaWiki API, 2026-10-27); the house: 1 tile from the edge of its 2 x 2 tiles
WIKI = {"ARCHERY_RANGE": 6, "BARRACKS": 6, "BLACKSMITH": 6, "BOMBARD_TOWER": 10, "CASTLE": 11, "DOCK": 8, "DONJON": 10,
        "FEITORIA": 6, "FORTIFIED_TOWER": 14, "GUARD_TOWER": 10, "HOUSE": 2, "KEEP": 10, "KREPOST": 10,
        "LUMBER_CAMP": 6, "MARKET": 6, "MILL": 6, "MINING_CAMP": 6, "MONASTERY": 6, "OUTPOST": 4, "SIEGE_WORKSHOP": 6,
        "STABLE": 6, "TOWN_CENTER": 8, "UNIVERSITY": 6, "WATCH_TOWER": 10, "WONDER": 8}
T = 4


def unit(name, player, x, y):
    return types.SimpleNamespace(name=name, player=player, pos=(x * T, 70.0, y * T))


def test_building_sight_is_the_wiki_value():
    assert {k: combat.sight(k) for k in WIKI} == WIKI


def test_seen_has_the_tiles_of_a_town_center_and_a_scout():
    tc = (1, "TOWN_CENTER", (40 * T, 44 * T, 40 * T, 44 * T))      # 4 x 4 tiles, center (42, 42)
    scout = unit("SCOUT_CAVALRY", 1, 70.5, 42.5)
    enemy = unit("SCOUT_CAVALRY", 2, 100.5, 100.5)
    s = replay.seen([scout, enemy], [tc, (2, "CASTLE", (90 * T, 94 * T, 90 * T, 94 * T))], 1, T)
    r = combat.sight("SCOUT_CAVALRY")
    assert {(42, 42), (49, 42), (42, 34), (36, 37)} <= s and (51, 42) not in s and (35, 35) not in s
    assert {(70, 42), (70 + r, 42), (70, 42 - r)} <= s and (71 + r, 42) not in s
    assert not {(x, y) for x, y in s if x > 80 or y > 60}            # no tile of player 2
    assert replay.seen([scout, enemy], [tc], 3, T) == set()
