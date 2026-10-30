"""game/data/monk.jsonl: one rule of monk.py, IMMUNE, NEXT or LASTING (#2034)."""
from . import form


def check(row):
    form(row, {"name": str}, {"immune": bool, "next": bool, "lasting": bool})
    assert len(row) == 2, row["name"]
