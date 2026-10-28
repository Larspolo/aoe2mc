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
    assert {"COSTS", "UNITS", "WORK", "WORK_RATE"} <= set(OLD)
    assert civs.KEYS["regen"].endswith("(#2247)") and "regeneration" in civs.KEYS["regen"]


@pytest.mark.parametrize("name", sorted(OLD))
def test_an_older_table_has_the_values_of_its_key(name):
    assert civs.frozen(getattr(civs, name)) == civs.BY_KEY[name.lower()]


def test_value_reads_a_key_and_gives_the_default_for_a_civilization_without_it():
    assert civs.value("economy_villagers", "WEI") == 1
    assert civs.value("economy_villagers", "BRITONS", 0) == 0
    assert civs.value("work_rate", "PERSIANS")["TOWN_CENTER"] == civs.WORK_RATE["PERSIANS"]["TOWN_CENTER"]
    with pytest.raises(AssertionError):
        civs.value("economy_villager", "WEI")                          # a misspelled key
