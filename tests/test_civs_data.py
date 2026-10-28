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
    assert train.UNIQUE == civs.UNIQUE and train.UNIQUE["BRITONS"] == "LONGBOWMAN"


def test_missing_is_by_item_as_before():
    assert civs.MISSING["KREPOST"] and "BULGARIANS" not in civs.MISSING["KREPOST"]
    assert set(civs.ELEPHANTS) == {"BENGALIS", "BURMESE", "DRAVIDIANS", "KHMER", "MALAY", "VIETNAMESE"}
    assert all(list(cs) == sorted(cs) for cs in civs.MISSING.values())


def test_the_blacksmith_and_economy_bonuses_name_the_whole_lists():
    """civs.SMITH and civs.ECONOMY name the technologies of the cost bonuses that cover a whole building group."""
    whats = {c: [what for what, *_ in b] for c, b in civs.COSTS.items()}
    assert all(civs.SMITH in whats[c] for c in ("BULGARIANS", "SPANISH"))
    assert all(civs.ECONOMY in whats[c] for c in ("BURGUNDIANS", "VIETNAMESE"))
