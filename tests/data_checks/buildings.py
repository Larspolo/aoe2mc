"""game/data/buildings.jsonl: the combat values of a building, or only its line of sight (#1913)."""
from . import NAMES, NUMBER, STATS, form, stats


def check(row):
    if "hp" in row:
        form(row, {"name": str, **STATS, "sight": int}, {"as": str, "min_range": NUMBER, "note": str, "garrison": int,
                                                         "arrows": int})
        stats(row)
        assert row.get("as", "HOUSE") in NAMES["buildings.jsonl"], row["name"]   # combat.STANDS_FOR
    else:                                                  # no target, or a wall of the game program (combat.WALLS)
        form(row, {"name": str}, {"sight": int, "note": str, "garrison": int})
        assert len(row) > 1, row["name"]
