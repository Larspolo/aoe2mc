"""game/data/xs_constants.jsonl: a built-in constant of the AoE2 DE XS API (Constants.xs, #5807), with one value key."""
from . import form


def check(row):
    form(row, {"name": str}, {"int": int, "string": str, "vector": list})
    assert row["name"].startswith("c") and len(set(row) & {"int", "string", "vector"}) == 1, row["name"]
    assert len(row.get("vector", [0, 0, 0])) == 3, row["name"]
