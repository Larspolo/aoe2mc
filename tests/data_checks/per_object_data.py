"""game/data/per_object_data.jsonl: an ObjectData of an AI script (up-get-object-data, #4959)."""
from game import per

from . import form


def check(row):
    form(row, {"name": str, "id": int}, {"value": str})
    assert row["name"].startswith("object-data-") and row["id"] >= -1, row["name"]
    assert row.get("value", "id") in per.OBJECT_VALUES, row["name"]
