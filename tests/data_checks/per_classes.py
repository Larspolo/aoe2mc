"""game/data/per_classes.jsonl: an object class or a projectile type of an AI script (#4966)."""
from . import NAMES, form


def check(row):
    form(row, {"name": str, "kind": str, "id": int}, {"armor": list, "units": list, "buildings": list, "building": bool,
                                                     "any": bool})
    n = row["name"]
    assert row["kind"] in ("class", "projectile") and n == n.lower() and row["id"] >= 0, n
    assert sum(k in row for k in ("armor", "units", "buildings", "building", "any")) == 1, n
    assert set(row.get("buildings", ())) <= NAMES["buildings.jsonl"] | NAMES["build.jsonl"] and set(row.get("units", ())) <= NAMES["units.jsonl"], n
