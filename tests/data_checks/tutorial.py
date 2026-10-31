"""game/data/tutorial.jsonl: a step of the tutorial (#5161)."""
from . import form


def check(row):
    form(row, {"name": str, "text": str, "check": str, "controls": list}, {"need": int})
    assert row["check"].count(".") == 1, row["name"]
