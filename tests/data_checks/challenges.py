"""game/data/challenges.jsonl: an Art of War challenge, its medal limits (#3761)."""
from . import NAMES, form

KEYS = {                                                   # the optional keys of a challenge: one per line (#3907)
    "after": (str, type(None)),
    "attacks": list,
    "check": str,
    "enemy": dict,
    "kills": int,
    "need": dict,
}


def check(row):
    form(row, {"name": str, "civ": str, "goal": str, "medal": str, "gold": int, "silver": int, "bronze": int,
               "note": str}, KEYS)
    assert row["civ"] in NAMES["civs.jsonl"] and row["medal"] in ("time", "lost"), row["name"]
    assert 0 <= row["gold"] < row["silver"] < row["bronze"] and row["note"].startswith("AoE2 wiki"), row["name"]
    assert row["after"] is None or row["after"] in NAMES["challenges.jsonl"], row["name"]
