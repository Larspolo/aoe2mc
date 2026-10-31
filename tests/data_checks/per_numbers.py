"""game/data/per_numbers.jsonl: a strategic number of an AI script (#4685)."""
from . import form


def check(row):
    form(row, {"name": str, "id": int, "default": int, "note": str})
    assert row["name"].startswith("sn-") and row["name"] == row["name"].lower(), row["name"]
