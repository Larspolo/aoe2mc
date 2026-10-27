"""The combat properties of game/combat.py (blast, minimum range, pass-through, melee damage from a range, building
sight, walls) are keys of the lines in game/data/units.jsonl and buildings.jsonl (#2032). Form tests only (#2008)."""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "game")]
import combat  # noqa: E402


def test_each_unit_property_belongs_to_a_unit_with_stats():
    for table in (combat.MELEE_RANGED, combat.BLAST, combat.MIN_RANGE, combat.PASS, combat.PASS_PART,
                  combat.BUILDING_SIGHT):
        assert set(table) <= set(combat.STATS)


def test_the_values_have_the_right_form():
    assert all(isinstance(v, (int, float)) and v >= 0 for t in (combat.BLAST, combat.MIN_RANGE, combat.PASS,
                                                                  combat.PASS_PART, combat.FORT_MIN_RANGE) for v in t.values())
    assert set(combat.BUILDING_SIGHT.values()) <= {"only", "first"}
    assert set(combat.PASS_PART) <= set(combat.PASS)


def test_the_walls_are_no_building_target_and_have_four_ages():
    assert combat.WALLS and not set(combat.WALLS) & set(combat.BUILDINGS)
    assert all(len(hp) == 4 and isinstance(m, int) and isinstance(p, int) for hp, m, p in combat.WALLS.values())
    assert set(combat.FORT_MIN_RANGE) <= set(combat.BUILDINGS)
