"""game/data/per_resources.jsonl: a ResourceType of an AI script (up-resource-amount, #4964)."""
from . import form


def check(row):
    form(row, {"name": str, "id": int}, {"source": str})
    assert row["name"] == row["name"].lower() and row["id"] >= 0, row["name"]
    assert row.get("source", "relics") in ("relics", "population", "population-cap", "current-age",
                                           "civilian-population", "military-population") \
        or row["source"].removesuffix("-amount") in ("food", "wood", "gold", "stone"), row["name"]
