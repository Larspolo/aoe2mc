"""game/data/train.jsonl: a menu item of a building (#1702)."""
from . import NAMES, RES, form, only

# The keys with two types by design: an "effect" is data, a list of data (#2155) or the name of a function of
# game/train.py (#2098, #2122)
TWO_TYPES = {"detonate": (dict, list),                     # one blast, or one per unit line (#4367)
             "effect": (dict, list, str)}


def check(row):
    form(row, {"name": str, "building": (str, type(None)), "slot": int, "item": str, "label": str, "cost": dict,
               "time": int, "help": str},
         {"age": int, "after": str, "civ": str, "civs": list, "faster": list, "upgrade": list, "note": str,
          "resist": int, "tribute_fee": int, "full_tech_tree": str, "doctrine": bool, "not_civs": list})
    n = row["name"]
    only(row)
    assert row["building"] is None or row["building"] in NAMES["buildings.jsonl"], n
    assert 0 <= row["slot"] < 54 and (row["time"] > 0 or row.get("doctrine") or row.get("toggle")) and row.get("age", 1) in (1, 2, 3), n
    assert set(row["cost"]) <= RES and all(isinstance(v, int) and v >= 0 for v in row["cost"].values()), n
    assert 0 < len(row["help"]) <= 50 and row["label"] and row["item"] == row["item"].lower(), n   # the menu width
    assert row.get("after", n) in NAMES["train.jsonl"] and row.get("after") != n, n
    assert row.get("civ", "BRITONS") in NAMES["civs.jsonl"], n                  # a unique technology of the castle
    if "faster" in row:                                    # the age and the train time from it (#2155)
        assert row["faster"][0] in (1, 2, 3) and 0 < row["faster"][1] < row["time"], n
    if "upgrade" in row:
        pairs = row["upgrade"] if isinstance(row["upgrade"][0], list) else [row["upgrade"]]
        assert all(len(p) == 2 and set(p) <= NAMES["units.jsonl"] for p in pairs), n
