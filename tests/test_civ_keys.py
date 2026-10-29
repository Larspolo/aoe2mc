"""game/civs.py: each key of data/civs.jsonl has its line in data/civ_keys.jsonl, and BY_KEY holds its values (#2281).
A new civilization bonus key then needs no new line of game/civs.py, so parallel civ tickets do not conflict there."""
import pytest

from game import civs, table

# The older tables have the name of their key in capitals and the same values as BY_KEY (frozen: lists as tuples). Not
# so: MISSING, SHARED and NOT_SHARED, the tables by item (also from the key "civs" of other data files), and EARLIER (sets).
OLD = sorted(k.upper() for k in civs.KEYS if hasattr(civs, k.upper())
             and k not in ("earlier", "shared", "not_shared"))


def test_each_key_of_a_civilization_line_has_its_description():
    keys = {k for r in table.load("civs.jsonl") for k in r} - {"name"}
    assert sorted(keys - set(civs.KEYS)) == [], "give each new key its line in game/data/civ_keys.jsonl (#2281)"


@pytest.mark.parametrize("name", sorted(OLD))
def test_an_older_table_has_the_values_of_its_key(name):
    assert civs.frozen(getattr(civs, name)) == civs.BY_KEY[name.lower()]


def test_value_reads_a_key_and_gives_the_default_for_a_civilization_without_it():
    have = civs.BY_KEY["economy_villagers"]
    assert all(civs.value("economy_villagers", c) == v for c, v in have.items())
    without = next(r["name"] for r in civs.ROWS if r["name"] not in have)
    assert civs.value("economy_villagers", without, 0) == 0
    assert all(civs.value("work_rate", c) == civs.WORK_RATE[c] for c in civs.WORK_RATE)
    with pytest.raises(AssertionError):
        civs.value("economy_villager", "WEI")                          # a misspelled key
