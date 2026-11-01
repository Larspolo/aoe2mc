"""game/data/tutorial.jsonl: a step of the tutorial (#5161)."""
from . import form


def check(row):
    form(row, {"name": str, "text": str, "check": str, "controls": list}, {"need": int, "raid": dict, "tip": str})
    assert row["check"].count(".") == 1, row["name"]
    assert all(isinstance(n, str) and isinstance(k, int) and k > 0 for n, k in row.get("raid", {}).items()), row["name"]
