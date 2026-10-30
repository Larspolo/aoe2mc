"""game/data/civ_keys.jsonl: a key of civs.jsonl, what it does, its issue (#2281)."""
from . import form


def check(row):
    form(row, {"name": str, "text": str, "issue": int})
    assert row["text"] and row["issue"] > 0, row["name"]
