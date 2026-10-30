"""game/data/build.jsonl: a building of the build menu, or only the age or technology of a name (#2028)."""
from . import NAMES, RES, form, only


def check(row):
    form(row, {"name": str}, {"cost": dict, "time": int, "icon": str, "age": int, "needs": str, "gate": bool,
                              "wall": bool, "age_tech": int, "bot": int, "near": str, "civs": list,
                              "full_tech_tree": str, "military": bool, "not_civs": list})
    n = row["name"]
    only(row)
    assert set(row.get("cost", {})) <= RES and all(isinstance(v, int) for v in row.get("cost", {}).values()), n
    assert row.get("time", 1) > 0 and row.get("age", 1) in (1, 2, 3), n
    assert row.get("needs", "HOUSE") in NAMES["build.jsonl"] | NAMES["train.jsonl"], n
