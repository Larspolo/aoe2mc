"""game/data/setup_keys.jsonl: a key of setup.jsonl, its type, what it does, its issue (#2558)."""
from . import form

TYPES = {"bool": bool, "dict": dict, "float": float, "int": int, "list": list, "str": str}


def check(row):
    form(row, {"name": str, "type": str, "text": str, "issue": int}, {"kind": bool})
    assert row["type"] in TYPES and row["text"] and row["issue"] > 0, row["name"]
