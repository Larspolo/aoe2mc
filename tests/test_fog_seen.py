"""The tiles that the own units, buildings and construction sites of the player see in the game program (#1388)."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import gather  # noqa: E402

T = 4


def bare(objects=(), sites=()):
    g = gather.Gather.__new__(gather.Gather)
    g.player, g.data, g.map = 1, {"objects": list(objects)}, types.SimpleNamespace(T=T)
    g.villagers, g.soldiers, g.sites = {"v": None}, {"m": "MILITIA", "a": "ARCHER"}, list(sites)
    return g


def circle(x, y, r):
    """The tiles of a circle of r tiles around the center of tile (x, y)."""
    return {(i, j) for i in range(x - r, x + r + 1) for j in range(y - r, y + r + 1) if (i - x) ** 2 + (j - y) ** 2 <= r * r}


def test_each_own_unit_building_and_site_adds_its_circle():
    tc = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [40 * T, 40 * T, 44 * T, 44 * T]}
    castle = {"kind": "building", "name": "CASTLE", "player": 2, "footprint": [90 * T, 90 * T, 94 * T, 94 * T]}
    site = {"name": "HOUSE", "player": 1, "footprint": (10 * T, 12 * T, 70 * T, 72 * T), "progress": 1.0}
    g = bare([tc, castle], [site])
    pos = {"v": (20.5 * T, 70.0, 20.5 * T), "m": (60.5 * T, 70.0, 20.5 * T), "a": (100.5 * T, 70.0, 20.5 * T),
           "e": (20.5 * T, 70.0, 60.5 * T)}                          # e: an enemy unit, not own
    s = g.seen_tiles(pos)
    assert circle(20, 20, combat.sight("VILLAGER")) <= s and (20 + combat.sight("VILLAGER") + 1, 20) not in s
    assert circle(60, 20, combat.sight("MILITIA")) <= s
    assert (100 + combat.sight("ARCHER"), 20) in s and (101 + combat.sight("ARCHER"), 20) not in s
    assert (42, 42 - combat.sight("TOWN_CENTER")) in s and (42, 41 + combat.sight("TOWN_CENTER") + 2) not in s
    assert {(11, 70 + combat.sight("HOUSE")), (10, 72)} <= s and (11, 73) not in s   # a complete house site sees too
    assert not {(x, y) for x, y in s if y > 50 and x < 30} - circle(11, 71, combat.sight("HOUSE") + 1)   # not e
    assert not {(x, y) for x, y in s if x > 80 and y > 60}             # not the castle of player 2


def test_a_dead_unit_and_no_unit_see_nothing():
    assert bare().seen_tiles({"x": (0.5, 70.0, 0.5)}) == set()
