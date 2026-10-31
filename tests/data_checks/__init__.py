"""The form checks of the data files of the game program (#1916): one module per file of game/data/, named as the file
(units.py checks units.jsonl), with check(row). tests/test_data_files.py finds the modules by itself (pkgutil, no list,
#4778): a new data file adds one module, and a new key changes only the module of its file. This file has the shared
parts."""
import os

from game import combat, table

RES = {"food", "wood", "gold", "stone"}


def rows(name):
    return table.load(name)


NAMES = {f: {r["name"] for r in rows(f)} for f in sorted(os.listdir(table.DIR)) if f.endswith(".jsonl")}   # not antiquity/
CLASSES = {c for f in ("units.jsonl", "buildings.jsonl") for r in rows(f) for c in r.get("classes", ())}
NUMBER = (int, float)


def form(row, need, may=()):
    """The keys of row: all of need, each of need and may ({key: type}) with its type. Another key is new: a parallel
    ticket can add one, so test_each_key_has_one_type checks it until it gets its type here."""
    keys = {**need, **dict(may)}
    assert set(need) <= set(row), (row["name"], sorted(set(need) - set(row)))
    for k, v in row.items():
        if k in keys:
            assert isinstance(v, keys[k]) and (keys[k] is bool or not isinstance(v, bool)), (row["name"], k, v)


STATS = {"hp": int, "attack": int, "melee": int, "pierce": int, "range": NUMBER, "reload": float, "bonus": dict,
         "classes": list}
OPTIONAL = {"blast", "passes", "pass_part"}                  # a field of combat.Stats with a default (#4283)


def stats(row):
    assert set(combat.Stats._fields) - OPTIONAL == set(STATS)
    assert row["hp"] > 0 and row["attack"] >= 0 and row["range"] >= 0 and row["reload"] >= 0, row["name"]
    assert set(row["classes"]) <= CLASSES and len(set(row["classes"])) == len(row["classes"]), row["name"]
    bonus = CLASSES | {combat.STANDARD, combat.STONE, combat.WALL}   # the code adds these classes to the buildings
    assert set(row["bonus"]) <= bonus and all(isinstance(v, int) for v in row["bonus"].values()), row["name"]


def only(row):
    """The key "civs" (#2235): the civilizations that have the item; "not_civs" (#3200): those that do not have it.
    Sorted, fewer than all, and one form for each item."""
    for k in ("civs", "not_civs"):
        cs = row.get(k, ["BRITONS"])
        assert cs and cs == sorted(set(cs)) and set(cs) < NAMES["civs.jsonl"], row["name"]
    assert not {"civs", "not_civs"} <= set(row), row["name"]
