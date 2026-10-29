"""The civilization tables in game/data/civs.jsonl (#1914): the form of each line, and the dicts built from it."""
import re

from game import civs, table, train

AGES = 4


def test_each_line_has_a_civilization_name():
    rows = table.load("civs.jsonl")
    assert [r["name"] for r in rows] == sorted(r["name"] for r in rows)        # one line per civ, in name order
    for r in rows:                                 # another key: tests/test_data_keys.py (#2188)
        assert re.fullmatch(r"[A-Z_]+", r["name"])


def test_the_bonuses_have_a_change_for_each_age():
    for table_ in (civs.UNITS, civs.COSTS):
        for c, bonuses in table_.items():
            for what, value, change in bonuses:
                assert isinstance(what, (str, tuple)) and (value is None or isinstance(value, str)), c
                assert len(change) == AGES and all(isinstance(x, (int, float)) for x in change), c
    assert all(g in civs.GROUPS for b in civs.UNITS.values() for g, *_ in b)


def test_the_names_are_items_of_the_menus():
    known = set(train.COSTS) | set(train.build.COSTS)                       # a typo in a name hides nothing
    assert set(civs.NOT) <= known
    assert {n for b in civs.COSTS.values() for what, *_ in b if isinstance(what, tuple) for n in what} <= known
    assert {n for t in civs.TWICE.values() for n in t} <= known
    assert train.UNIQUE == civs.UNIQUE


def test_missing_is_sorted():
    assert all(list(cs) == sorted(cs) for cs in civs.MISSING.values())
