"""game/data/lang_plain.jsonl: a function of game/ that may send a plain "text" component (tests/test_lang_scan.py,
#5379), as module.function, and why."""
from . import form


def check(row):
    form(row, {"name": str, "note": str})
    assert row["name"].count(".") >= 1 and row["note"], row["name"]
