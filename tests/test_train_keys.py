"""The name tables of game/train.py come from keys of the lines of game/data/*.jsonl (#2030): a new speed bonus,
requirement, upgrade or house is one key on its line. The tests check the form of the keys, not their values."""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "game")]
import combat  # noqa: E402
import train  # noqa: E402


def test_the_building_keys_name_buildings_with_numbers():
    for table in (train.HOUSING, train.ARROWSLITS, train.HEATED):
        assert table and all(n in combat.BUILDINGS and isinstance(v, int) and v > 0 for n, v in table.items())
    assert train.CONSCRIPT[0] and set(train.CONSCRIPT[0]) <= set(train.TRAINS) and train.CONSCRIPT[1] > 1


def test_the_unit_keys_name_units():
    for names in (train.HULKS, train.ORDERS):
        assert names and set(names) <= set(combat.STATS)


def test_the_technology_keys_name_technologies_and_buildings():
    for table in (train.BY_KEY["walk"], train.BY_KEY["walls"], train.BY_KEY["towers"], train.REQUIRES):
        assert table and set(table) <= set(train.COSTS)
    assert all(isinstance(u, str) for unit, _ in train.BY_KEY["walk"].values() for u in (unit if isinstance(unit, list) else [unit]))
    assert all(f > 1 for _, f in train.BY_KEY["walk"].values())
    for n, (count, names, *alone) in train.REQUIRES.items():
        assert 0 < count <= len(names) and all(set(b) <= set(combat.BUILDINGS) for b in (names, *alone)), n
    for t, towers in train.BY_KEY["towers"].items():
        assert train.BY_KEY["after"].get(t) in (None, *list(train.BY_KEY["towers"])[:list(train.BY_KEY["towers"]).index(t)]), t
