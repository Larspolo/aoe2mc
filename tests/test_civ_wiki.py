"""The civilization bonus tables of game/civs.py against the full list of the AoE2 DE wiki bonuses (#1896, epic #1088).

tests/data/civ_bonuses.jsonl is a copy of the "Civilization bonuses" of each civilization page of the AoE2 wiki (not the
team bonuses and the unique technologies). Each bonus has one state: "in" names the table of game/civs.py that holds
it (or the game/ file that has it); "gap" names the roadmap key of a bonus whose part the game program has, but not the
bonus yet (a ticket can add it); "later" names the roadmap key of the part that the game program does not have yet.
One line per bonus, with the name "CIV: bonus", so that tools/merge_jsonl.py merges two tickets by line (#2100)."""
import json
import os
import re

import buildings
from game import civs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BONUSES = {}                                                           # civ -> [{"bonus": ..., state: ...}], in file order
with open(os.path.join(ROOT, "tests", "data", "civ_bonuses.jsonl")) as f:
    for r in map(json.loads, f):
        BONUSES.setdefault(r.pop("civ"), []).append(r)
TABLES = (                                                            # one per line: parallel tickets add one
    "AGE_GIFTS",
    "AGE_NO_BUILDINGS",
    "AGE_RATE",
    "AGE_VILLAGERS",
    "ARROWS",
    "BUILD_OF",
    "COSTS",
    "GARRISON",
    "REPAIR",
    "REPAIR_COST",
    "START",
    "TRAIN_RATE",
    "TWICE",
    "UNITS",
    "WORK",
)
KEYS = set(re.findall(r"`(play:[a-z-]+)`", open(os.path.join(ROOT, "docs", "ROADMAP.md")).read()))


def test_each_civilization_is_in_the_list():
    known = {c for v in buildings.CIV_ARCH.values() for c in v.split()}
    assert set(BONUSES) == known and list(BONUSES) == sorted(BONUSES)


def test_each_bonus_has_one_known_state():
    for civ, rows in BONUSES.items():
        for r in rows:
            state = set(r) - {"bonus", "name"}
            assert len(state) == 1 and r["bonus"] and r["name"] == f"{civ}: {r['bonus']}", (civ, r)
            if "in" in r:
                assert r["in"] in TABLES or os.path.isfile(os.path.join(ROOT, r["in"])), (civ, r)
            else:
                assert r.get("gap", r.get("later")) in KEYS, (civ, r)


def test_each_bonus_of_a_table_has_its_entry():
    missing = []
    for civ, rows in BONUSES.items():
        for r in rows:
            if r.get("in") in TABLES and civ not in getattr(civs, r["in"]):
                missing.append((civ, r["in"], r["bonus"]))
            elif r.get("in", "").startswith("game/"):
                with open(os.path.join(ROOT, r["in"])) as f:
                    if f'"{civ}"' not in f.read():
                        missing.append((civ, r["in"], r["bonus"]))
    assert not missing


def test_each_table_entry_is_a_bonus_of_the_list():
    """The other way: an entry of a table with no bonus of that state in the list is a bonus that the wiki does not
    name, or a list that is not up to date. Not REPAIR (the Roman villager bonus of WORK) and REPAIR_COST (a team
    bonus)."""
    for name in set(TABLES) - {"REPAIR", "REPAIR_COST"}:
        for civ in getattr(civs, name):
            assert any(r.get("in") == name for r in BONUSES[civ]), (name, civ)
