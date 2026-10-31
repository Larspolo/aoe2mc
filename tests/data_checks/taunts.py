"""game/data/taunts.jsonl: a taunt, its number and AoE2 text (#2234)."""
from . import form


def check(row):
    form(row, {"name": str, "text": str}, {"sound": str, "answer": str, "focus": str})   # sound: a vanilla match (#2662); answer: #4829; focus: #4886
    assert row["name"].isdigit() and row["name"] == str(int(row["name"])) and row["text"], row["name"]
