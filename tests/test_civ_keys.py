"""game/civs.py: each key of data/civs.jsonl has its line in data/civ_keys.jsonl, and BY_KEY holds its values (#2281).
A new civilization bonus key then needs no new line of game/civs.py, so parallel civ tickets do not conflict there."""
import pytest

from game import civs, table

# The older tables and their keys: they hold the same values as BY_KEY (frozen: lists as tuples).
OLD = {"ALSO": "also", "AGE_GIFTS": "age_gifts", "ARROWS": "arrows", "BUILD": "build", "BUILD_OF": "build_of",
       "BUILD_WONDER": "build_wonder", "COST_PER": "cost_per", "COSTS": "costs", "DROP": "drop", "EXTRA": "extra",
       "FARM_UPGRADES": "farm_upgrades", "GARRISON": "garrison", "HP": "hp", "HP_AGE": "hp_age", "LAST": "last",
       "MORE": "more", "REGEN": "regen", "REPAIR": "repair", "REPAIR_COST": "repair_cost",
       "REPAIR_TEAM": "repair_team", "RESEARCH_TIME": "research_time", "SMITH_UNITS": "smith_units",
       "START": "start", "TECH_GIFTS": "tech_gifts", "TRAIN_RATE": "train_rate", "TWICE": "twice",
       "UNIQUE": "unique", "UNITS": "units", "WORK": "work", "WORK_RATE": "work_rate"}


def test_each_key_of_a_civilization_line_has_its_description():
    keys = {k for r in table.load("civs.jsonl") for k in r} - {"name"}
    assert sorted(keys - set(civs.KEYS)) == []
    assert civs.KEYS["regen"].endswith("(#2247)") and "regeneration" in civs.KEYS["regen"]


@pytest.mark.parametrize("name", sorted(OLD))
def test_an_older_table_has_the_values_of_its_key(name):
    assert civs.frozen(getattr(civs, name)) == civs.BY_KEY[OLD[name]]


def test_value_reads_a_key_and_gives_the_default_for_a_civilization_without_it():
    assert civs.value("economy_villagers", "WEI") == 1
    assert civs.value("economy_villagers", "BRITONS", 0) == 0
    assert civs.value("work_rate", "PERSIANS")["TOWN_CENTER"] == civs.WORK_RATE["PERSIANS"]["TOWN_CENTER"]
    with pytest.raises(AssertionError):
        civs.value("economy_villager", "WEI")                          # a misspelled key
