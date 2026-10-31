"""game/data/music.jsonl: a music track of the game program, its use and its length in real seconds (#5341)."""
from tools import mcvalid

from . import form


def check(row):
    form(row, {"name": str, "use": str, "seconds": int})
    assert mcvalid.sound_error(row["name"]) is None and row["use"] in ("peace", "battle") and row["seconds"] > 0, row["name"]
