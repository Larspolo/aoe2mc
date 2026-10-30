"""The civilization bonus tables of game/civs.py against the full list of the AoE2 DE wiki bonuses (#1896, epic #1088).

tests/data/civ_bonuses.jsonl is a copy of the "Civilization bonuses" of each civilization page of the AoE2 wiki (not the
team bonuses and the unique technologies). Each bonus has one state: "in" names the table of game/civs.py that holds
it, its key of game/data/civs.jsonl (civs.KEYS, #2281) or the game/ file that has it; "gap" names the roadmap key of a bonus whose part the game program has, but not the
bonus yet (a ticket can add it); "later" names the roadmap key of the part that the game program does not have yet.
A bonus of two tables lists both ("in": [...], the Khitan
upgrade one age earlier and at half cost, #2268). One line per bonus, with the name "CIV: bonus", so that framework/tools/merge_jsonl.py merges two tickets by line (#2100)."""
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


def ins(r):
    """The tables or files of the state "in" of bonus r: one name or a list of names."""
    return r["in"] if isinstance(r.get("in"), list) else [r["in"]] if "in" in r else []


# The tables of game/civs.py that the list names: no list of names here, so parallel tickets with a new table do not
# conflict (#2239). A typo in an "in" value is no name of civs and no file: test_each_bonus_has_one_known_state fails.
TABLES = sorted({t for rows in BONUSES.values() for r in rows for t in ins(r) if t.isupper() and hasattr(civs, t)})
KEYS = set(re.findall(r"`(play:[a-z-]+)`", open(os.path.join(ROOT, "steering", "project", "ROADMAP.md")).read()))


def test_each_civilization_is_in_the_list():
    known = {c for v in buildings.CIV_ARCH.values() for c in v.split()}
    assert set(BONUSES) == known and list(BONUSES) == sorted(BONUSES)


def test_each_bonus_has_one_known_state():
    for civ, rows in BONUSES.items():
        for r in rows:
            state = set(r) - {"bonus", "name"}
            assert len(state) == 1 and r["bonus"] and r["name"] == f"{civ}: {r['bonus']}", (civ, r)
            if "in" in r:
                assert r["in"] and all(t in TABLES or t in civs.KEYS or os.path.isfile(os.path.join(ROOT, t)) for t in ins(r)), (civ, r)
            else:
                assert r.get("gap", r.get("later")) in KEYS, (civ, r)


def test_each_table_is_keyed_by_civilizations():
    known = {c for v in buildings.CIV_ARCH.values() for c in v.split()}
    for name in TABLES:
        table = getattr(civs, name)
        assert isinstance(table, (dict, tuple)) and set(table) <= known, name


def test_each_bonus_of_a_table_has_its_entry():
    missing = []
    for civ, rows in BONUSES.items():
        for r in rows:
            for t in ins(r):
                if t in TABLES and civ not in getattr(civs, t):
                    missing.append((civ, t, r["bonus"]))
                elif t.startswith("game/"):
                    with open(os.path.join(ROOT, t)) as f:
                        if f'"{civ}"' not in f.read():
                            missing.append((civ, t, r["bonus"]))
    assert not missing


def test_each_table_entry_is_a_bonus_of_the_list():
    """The other way: an entry of a table with no bonus of that state in the list is a bonus that the wiki does not
    name, or a list that is not up to date. Not BUILD and REPAIR (the Roman villager bonus of WORK) and REPAIR_COST (a
    team bonus). Not a TRAINS entry after a unique technology (its key "after": the Goth barracks after Anarchy, #2685)."""
    for name in set(TABLES) - {"BUILD", "REPAIR", "REPAIR_COST"}:
        for civ in getattr(civs, name):
            if name == "TRAINS" and all("after" in b for b in civs.TRAINS[civ].values()):
                continue
            assert any(name in ins(r) for r in BONUSES[civ]), (name, civ)
