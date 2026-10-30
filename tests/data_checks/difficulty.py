"""game/data/difficulty.jsonl: a level of "AI difficulty" of the bot (#2661)."""
from . import NUMBER, form


def check(row):
    form(row, {"name": str, "aoe2": int, "gather": NUMBER, "attack": NUMBER, "soldiers": int, "note": str})
    assert row["gather"] > 0 and row["attack"] > 0 and row["soldiers"] >= 1, row["name"]
