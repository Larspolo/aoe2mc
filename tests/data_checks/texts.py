"""game/data/texts.jsonl: a translate key of the game program and its English text, the fallback (#5344)."""
from . import form


def check(row):
    form(row, {"name": str, "en_us": str})
    assert row["name"].startswith("aoe2mc.") and row["en_us"], row["name"]
