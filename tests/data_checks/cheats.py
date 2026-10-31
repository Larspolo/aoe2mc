"""game/data/cheats.jsonl: a cheat code, its unit or a transform (#2034)."""
from . import form


def check(row):
    form(row, {"name": str}, {"unit": str, "transform": str, "units": list, "rule": str, "note": str})
    assert ("unit" in row) != ("transform" in row) and ("units" in row) + ("rule" in row) == ("transform" in row), row["name"]
    assert row["name"] == row["name"].lower(), row["name"]
