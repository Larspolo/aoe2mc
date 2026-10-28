"""The data files of the game program have the right form (#1916): each line is JSON, the names are unique, the keys
and the value types are the expected ones, and each name that a line refers to exists. A new data line needs no test
of its values: the values come from the AoE2 wiki, and this file checks their form."""
import json
import os

import pytest

from game import build, civs, combat, table, train

RES = {"food", "wood", "gold", "stone"}


def rows(name):
    return table.load(name)


NAMES = {f: {r["name"] for r in rows(f)} for f in sorted(os.listdir(table.DIR))}
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


def stats(row):
    assert set(combat.Stats._fields) == set(STATS)
    assert row["hp"] > 0 and row["attack"] >= 0 and row["range"] >= 0 and row["reload"] >= 0, row["name"]
    assert set(row["classes"]) <= CLASSES and len(set(row["classes"])) == len(row["classes"]), row["name"]
    bonus = CLASSES | {combat.STANDARD, combat.STONE, combat.WALL}   # the code adds these classes to the buildings
    assert set(row["bonus"]) <= bonus and all(isinstance(v, int) for v in row["bonus"].values()), row["name"]


def check_units(row):
    form(row, {"name": str, **STATS}, {"sight": int, "min_range": NUMBER, "note": str, "sail": NUMBER, "convert": int})
    stats(row)


def check_buildings(row):
    if "hp" in row:
        form(row, {"name": str, **STATS, "sight": int}, {"as": str, "min_range": NUMBER, "note": str, "garrison": int,
                                                         "arrows": int})
        stats(row)
        assert row.get("as", "HOUSE") in NAMES["buildings.jsonl"], row["name"]   # combat.STANDS_FOR
    else:                                                  # no target, or a wall of the game program (combat.WALLS)
        form(row, {"name": str}, {"sight": int, "note": str, "garrison": int})
        assert len(row) > 1, row["name"]


def check_train(row):
    form(row, {"name": str, "building": (str, type(None)), "slot": int, "item": str, "label": str, "cost": dict,
               "time": int, "help": str},
         {"age": int, "after": str, "civ": str, "civs": list, "faster": list, "upgrade": list, "note": str,
          "resist": int, "tribute_fee": int})
    n = row["name"]
    only(row)
    assert row["building"] is None or row["building"] in NAMES["buildings.jsonl"], n
    assert 0 <= row["slot"] < 54 and row["time"] > 0 and row.get("age", 1) in (1, 2, 3), n
    assert set(row["cost"]) <= RES and all(isinstance(v, int) and v >= 0 for v in row["cost"].values()), n
    assert 0 < len(row["help"]) <= 50 and row["label"] and row["item"] == row["item"].lower(), n   # the menu width
    assert row.get("after", n) in NAMES["train.jsonl"] and row.get("after") != n, n
    assert row.get("civ", "BRITONS") in NAMES["civs.jsonl"], n                  # a unique technology of the castle
    if "faster" in row:                                    # the age and the train time from it (#2155)
        assert row["faster"][0] in (1, 2, 3) and 0 < row["faster"][1] < row["time"], n
    if "upgrade" in row:
        pairs = row["upgrade"] if isinstance(row["upgrade"][0], list) else [row["upgrade"]]
        assert all(len(p) == 2 and set(p) <= NAMES["units.jsonl"] for p in pairs), n


def only(row):
    """The key "civs" (#2235): the civilizations that have the item, sorted, fewer than all."""
    cs = row.get("civs", ["BRITONS"])
    assert cs and cs == sorted(set(cs)) and set(cs) < NAMES["civs.jsonl"], row["name"]


def check_civ_keys(row):                                   # a key of civs.jsonl: what it does, its issue (#2281)
    form(row, {"name": str, "text": str, "issue": int})
    assert row["text"] and row["issue"] > 0, row["name"]


def check_civs(row):
    form(row, {"name": str, "missing": list}, {"unique": str})
    for k, v in row.items():                               # a rule, not a list of keys: parallel tickets add keys (#2239)
        assert isinstance(v, (dict, list, str, int, float)) and not isinstance(v, bool), (row["name"], k, v)
    n, known = row["name"], NAMES["train.jsonl"] | NAMES["units.jsonl"] | NAMES["buildings.jsonl"]
    assert set(row.get("drop", {})) <= {"food", "forage"} and all(isinstance(v, NUMBER) for v in row.get("drop", {}).values()), n
    assert set(row["missing"]) <= known and row["missing"] == sorted(set(row["missing"])), n
    assert not set(row["missing"]) & set(civs.ONLY), n                    # one form for each item (#2235)
    assert row.get("unique", "MILITIA") in NAMES["units.jsonl"], n
    assert set(row.get("twice", ())) <= NAMES["train.jsonl"], n
    assert len(row.get("hp_age", [1] * 4)) == 4 and all(isinstance(a, NUMBER) and a > 0 for a in row.get("hp_age", ())), n
    for t, group in row.get("also", {}).items():                   # one more group gets the effect (#2173)
        assert group in civs.GROUPS and isinstance(train.EFFECTS.get(t, {}), dict) and t in train.TECHS | train.SPEEDS, (n, t)
    assert all(t in train.TECHS and isinstance(f, NUMBER) for t, f in row.get("more", {}).items()), n
    for group, value, ages in row.get("units", ()):
        assert group in civs.GROUPS and value in (*combat.Stats._fields, "speed"), (n, group, value)
        assert len(ages) == 4 and all(isinstance(a, NUMBER) for a in ages), (n, group)
    for what, ages in row.get("arrows", ()):                 # the factor of the base arrows of buildings (#2178)
        assert set(what) <= NAMES["buildings.jsonl"] and len(ages) == 4 and all(isinstance(a, int) for a in ages), n
    for what, res, ages in row.get("costs", ()):
        names = NAMES["train.jsonl"] | set(build.COSTS)
        if isinstance(what, list):
            assert set(what) <= names, (n, what)
        else:                                              # a rule of civs.has that covers at least one name
            assert any(civs.has(what, x) for x in sorted(names | NAMES["units.jsonl"])), (n, what)
        assert res is None or res in RES, (n, what, res)
        assert len(ages) == 4 and all(isinstance(a, NUMBER) for a in ages), (n, what)
    for group, buildings, each, most in row.get("cost_per", ()):     # #2177
        assert group in civs.GROUPS and set(buildings) <= NAMES["buildings.jsonl"] and 0 < each <= most < 1, n


def check_gather(row):
    form(row, {"name": str}, {"drop": list, "work": dict, "fish": int, "shore": bool, "hunt": int, "herd": bool,
                              "farm": int, "dark": bool, "ship": list, "civilian": bool, "mine": list, "carry": int,
                              "pace": float, "watch": bool})
    n = row["name"]
    assert len(row) > 1 and set(row.get("drop", ())) <= RES | {"meat"} and set(row.get("work", {})) <= RES, n
    assert all(isinstance(v, NUMBER) for v in row.get("work", {}).values()), n
    if "mine" in row:                                      # [the resource, its amount, the villager name of the miner]
        res, amount, miner = row["mine"]
        assert res in RES and isinstance(amount, int) and miner.isupper(), n
    assert len(row.get("ship", (0, 0))) == 2 and all(isinstance(v, NUMBER) for v in row.get("ship", ())), n


def check_build(row):
    form(row, {"name": str}, {"cost": dict, "time": int, "icon": str, "age": int, "needs": str, "gate": bool,
                              "wall": bool, "age_tech": int, "bot": int, "near": str, "civs": list})
    n = row["name"]
    only(row)
    assert set(row.get("cost", {})) <= RES and all(isinstance(v, int) for v in row.get("cost", {}).values()), n
    assert row.get("time", 1) > 0 and row.get("age", 1) in (1, 2, 3), n
    assert row.get("needs", "HOUSE") in NAMES["build.jsonl"] | NAMES["train.jsonl"], n


def check_cheats(row):                                     # a cheat code: its unit, or a transform (#2034)
    form(row, {"name": str}, {"unit": str, "transform": str, "units": list, "rule": str, "note": str})
    assert ("unit" in row) != ("transform" in row) and ("units" in row) + ("rule" in row) == ("transform" in row), row["name"]
    assert row["name"] == row["name"].lower(), row["name"]


def check_monk(row):                                       # one rule of monk.py: IMMUNE, NEXT or LASTING (#2034)
    form(row, {"name": str}, {"immune": bool, "next": bool, "lasting": bool})
    assert len(row) == 2, row["name"]


def check_replay(row):                                     # a walk speed (a name start), an age or a Society building
    form(row, {"name": str}, {"walk": NUMBER, "age": int, "society": bool})
    assert len(row) == 2 and row.get("age", 1) in (1, 2, 3) and row.get("walk", 1) > 0, row["name"]


def check_taunts(row):                                     # a taunt: its number and AoE2 text (#2234)
    form(row, {"name": str, "text": str})
    assert row["name"].isdigit() and row["name"] == str(int(row["name"])) and row["text"], row["name"]


CHECKS = {"build.jsonl": check_build, "buildings.jsonl": check_buildings, "cheats.jsonl": check_cheats,
          "civ_keys.jsonl": check_civ_keys, "civs.jsonl": check_civs, "gather.jsonl": check_gather, "monk.jsonl": check_monk,
          "replay.jsonl": check_replay, "taunts.jsonl": check_taunts, "train.jsonl": check_train, "units.jsonl": check_units}


# The keys with two types by design: an "effect" is data, a list of data (#2155) or the name of a function of
# game/train.py (#2098, #2122)
TWO_TYPES = {("train.jsonl", "effect"): (dict, list, str)}


@pytest.mark.parametrize("name", sorted(NAMES))
def test_each_key_has_one_type(name):
    types = {}
    for row in rows(name):
        for k, v in row.items():
            if (name, k) in TWO_TYPES:
                assert isinstance(v, TWO_TYPES[name, k]), (name, row["name"], k)
                continue
            t = float if type(v) is int else type(v)       # an int is a float without a fraction; null: none
            assert v is None or types.setdefault(k, t) is t, (name, row["name"], k)


def test_the_effect_name_of_a_technology_is_a_function_of_train():
    from game import train
    for row in rows("train.jsonl"):
        assert callable(getattr(train, row.get("effect") if isinstance(row.get("effect"), str) else "effect")), row["name"]


@pytest.mark.parametrize("name", sorted(NAMES))
def test_each_line_is_one_json_object_with_a_unique_name(name):
    lines = [s for s in open(os.path.join(table.DIR, name), encoding="utf-8") if s.strip()]
    assert all(isinstance(json.loads(s), dict) for s in lines)
    assert len(rows(name)) == len(lines) == len(NAMES[name])      # table.load stops on a name in two lines


@pytest.mark.parametrize("name", sorted(NAMES))
def test_each_line_has_the_keys_and_the_names_of_its_file(name):
    for row in rows(name):
        CHECKS.get(name, lambda row: None)(row)            # a new file: give it an own check in CHECKS
