"""game/data/replay.jsonl: a walk speed (a name start), an age or a Society building (#2034)."""
from . import NUMBER, form


def check(row):
    form(row, {"name": str}, {"walk": NUMBER, "age": int, "society": bool})
    assert len(row) == 2 and row.get("age", 1) in (1, 2, 3) and row.get("walk", 1) > 0, row["name"]
