"""game/data/sounds.jsonl: a unit class, its select and order voice (#3499, #3500)."""
from . import form


def check(row):
    if row["name"].isupper():                              # a building: only the click sound (#3501)
        return form(row, {"name": str, "select": str, "pitch": float})
    form(row, {"name": str, "select": str, "order": str, "pitch": float})
