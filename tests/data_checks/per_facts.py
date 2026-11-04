"""game/data/per_facts.jsonl: a FactId of an AI script (up-get-fact with a number, #5808)."""
from . import form


def check(row):
    form(row, {"name": str, "id": int})
    assert row["name"] == row["name"].lower() and row["id"] >= 0, row["name"]
