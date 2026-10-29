"""The line of sight of the units and buildings of one player in the live replay (#1300)."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import replay  # noqa: E402

T = 4


def unit(name, player, x, y):
    return types.SimpleNamespace(name=name, player=player, pos=(x * T, 70.0, y * T))


def test_seen_has_the_tiles_of_a_town_center_and_a_scout():
    tc = (1, "TOWN_CENTER", (40 * T, 44 * T, 40 * T, 44 * T))      # 4 x 4 tiles, center (42, 42)
    scout = unit("SCOUT_CAVALRY", 1, 70.5, 42.5)
    enemy = unit("SCOUT_CAVALRY", 2, 100.5, 100.5)
    s = replay.seen([scout, enemy], [tc, (2, "CASTLE", (90 * T, 94 * T, 90 * T, 94 * T))], 1, T)
    r, rt = combat.sight("SCOUT_CAVALRY"), combat.sight("TOWN_CENTER")
    assert {(42, 42), (41 + rt, 42), (42, 42 - rt)} <= s and (42 + rt, 42) not in s and (42 - rt, 42 - rt) not in s
    assert {(70, 42), (70 + r, 42), (70, 42 - r)} <= s and (71 + r, 42) not in s
    assert not {(x, y) for x, y in s if x > 80 or y > 60}            # no tile of player 2
    assert replay.seen([scout, enemy], [tc], 3, T) == set()
