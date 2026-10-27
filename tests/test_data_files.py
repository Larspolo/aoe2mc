"""The data files of the game program have the right form (#1916): each line is JSON, the names are unique, the keys
and the value types are the expected ones, and each name that a line refers to exists. A new data line needs no test
of its values: the values come from the AoE2 wiki, and this file checks their form."""
import json
import os

import pytest

from game import build, civs, combat, table

RES = {"food", "wood", "gold", "stone"}


def rows(name):
    return table.load(name)


NAMES = {f: {r["name"] for r in rows(f)} for f in sorted(os.listdir(table.DIR))}
CLASSES = {c for f in ("units.jsonl", "buildings.jsonl") for r in rows(f) for c in r.get("classes", ())}
NUMBER = (int, float)


def form(row, need, may=()):
    """The keys of row: all of need, and only need and may ({key: type})."""
    keys = {**need, **dict(may)}
    assert set(need) <= set(row) <= set(keys), (row["name"], sorted(set(row) ^ set(need)))
    for k, v in row.items():
        assert isinstance(v, keys[k]) and not isinstance(v, bool), (row["name"], k, v)


STATS = {"hp": int, "attack": int, "melee": int, "pierce": int, "range": NUMBER, "reload": float, "bonus": dict,
         "classes": list}


def stats(row):
    assert set(combat.Stats._fields) == set(STATS)
    assert row["hp"] > 0 and row["attack"] >= 0 and row["range"] >= 0 and row["reload"] >= 0, row["name"]
    assert set(row["classes"]) <= CLASSES and len(set(row["classes"])) == len(row["classes"]), row["name"]
    bonus = CLASSES | {combat.STANDARD, combat.STONE}      # the code adds these two classes to the buildings
    assert set(row["bonus"]) <= bonus and all(isinstance(v, int) for v in row["bonus"].values()), row["name"]


def check_units(row):
    form(row, {"name": str, **STATS}, {"sight": int, "note": str})
    stats(row)


def check_buildings(row):
    if "hp" in row:
        form(row, {"name": str, **STATS, "sight": int}, {"note": str})
        stats(row)
    else:                                                  # only a line of sight: no target
        form(row, {"name": str, "sight": int}, {"note": str})


def check_train(row):
    form(row, {"name": str, "building": (str, type(None)), "slot": int, "item": str, "label": str, "cost": dict,
               "time": int, "help": str},
         {"age": int, "after": str, "civ": str, "upgrade": list, "note": str})
    n = row["name"]
    assert row["building"] is None or row["building"] in NAMES["buildings.jsonl"], n
    assert 0 <= row["slot"] < 54 and row["time"] > 0 and row.get("age", 1) in (1, 2, 3), n
    assert set(row["cost"]) <= RES and all(isinstance(v, int) and v >= 0 for v in row["cost"].values()), n
    assert 0 < len(row["help"]) <= 50 and row["label"] and row["item"] == row["item"].lower(), n   # the menu width
    assert row.get("after", n) in NAMES["train.jsonl"] and row.get("after") != n, n
    assert row.get("civ", "BRITONS") in NAMES["civs.jsonl"], n                  # a unique technology of the castle
    if "upgrade" in row:
        pairs = row["upgrade"] if isinstance(row["upgrade"][0], list) else [row["upgrade"]]
        assert all(len(p) == 2 and set(p) <= NAMES["units.jsonl"] for p in pairs), n


def check_civs(row):
    form(row, {"name": str, "missing": list}, {"unique": str, "units": list, "costs": list, "twice": list})
    n, known = row["name"], NAMES["train.jsonl"] | NAMES["units.jsonl"] | NAMES["buildings.jsonl"]
    assert set(row["missing"]) <= known and row["missing"] == sorted(set(row["missing"])), n
    assert row.get("unique", "MILITIA") in NAMES["units.jsonl"], n
    assert set(row.get("twice", ())) <= NAMES["train.jsonl"], n
    for group, value, ages in row.get("units", ()):
        assert group in civs.GROUPS and value in (*combat.Stats._fields, "speed"), (n, group, value)
        assert len(ages) == 4 and all(isinstance(a, NUMBER) for a in ages), (n, group)
    for what, res, ages in row.get("costs", ()):
        rules = ("buildings", "buildings but farms", "technologies", "ages")
        names = NAMES["train.jsonl"] | set(build.COSTS)
        assert set(what) <= names if isinstance(what, list) else what in civs.GROUPS or what in rules, (n, what)
        assert res is None or res in RES, (n, what, res)
        assert len(ages) == 4 and all(isinstance(a, NUMBER) for a in ages), (n, what)


CHECKS = {"buildings.jsonl": check_buildings, "civs.jsonl": check_civs, "train.jsonl": check_train,
          "units.jsonl": check_units}


def test_each_data_file_has_a_check():
    assert set(NAMES) == set(CHECKS)


@pytest.mark.parametrize("name", sorted(CHECKS))
def test_each_line_is_one_json_object_with_a_unique_name(name):
    lines = [s for s in open(os.path.join(table.DIR, name), encoding="utf-8") if s.strip()]
    assert all(isinstance(json.loads(s), dict) for s in lines)
    assert len(rows(name)) == len(lines) == len(NAMES[name])      # table.load stops on a name in two lines


@pytest.mark.parametrize("name", sorted(CHECKS))
def test_each_line_has_the_keys_and_the_names_of_its_file(name):
    for row in rows(name):
        CHECKS[name](row)
