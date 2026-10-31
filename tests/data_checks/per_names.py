"""game/data/per_names.jsonl: a name of an AI script, its name in the game (#4528)."""
from units import VILLAGER_JOBS

from . import NAMES, form


def check(row):
    form(row, {"name": str, "kind": str}, {"game": str, "age": int, "civ": str, "set": list, "task": list, "tiles": int, "id": int})
    assert row.get("civ") in (None, "unit", "elite", "upgrade", "research"), row["name"]
    assert all(n in NAMES["train.jsonl"] | NAMES["gather.jsonl"] for n in row.get("set", ())), row["name"]
    assert all(any(t == k for k, j in VILLAGER_JOBS) for t in row.get("task", ())) and (row["kind"] == "unit" or "task" not in row), row["name"]
    assert row["kind"] in ("age", "attribute", "building", "civ", "difficulty", "effect", "idle", "map-size", "map-type", "tech", "terrain", "unit") and row["name"] == row["name"].lower(), row["name"]
    games = {"civ": NAMES["civs.jsonl"], "difficulty": NAMES["difficulty.jsonl"]}.get(row["kind"], NAMES["train.jsonl"] | NAMES["build.jsonl"])
    assert "game" not in row or row["game"] in games, row["name"]
    assert ("tiles" in row) == (row["kind"] == "map-size"), row["name"]
    assert ("age" in row) == (row["kind"] == "age") and ("game" in row or row["kind"] in ("age", "attribute", "effect", "map-size", "map-type", "terrain")
                                                        or "civ" in row or "set" in row or "task" in row), row["name"]
