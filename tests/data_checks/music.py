"""game/data/music.jsonl: a music track of the game program, its use and its length in real seconds (#5341); a battle
track has the real seconds with no hit before the music goes back to peace ("calm", #5342)."""
from tools import mcvalid

from . import form


def check(row):
    form(row, {"name": str, "use": str, "seconds": int}, {"calm": int})
    assert mcvalid.sound_error(row["name"]) is None and row["use"] in ("peace", "battle") and row["seconds"] > 0, row["name"]
    assert (row["use"] == "battle") == ("calm" in row) and row.get("calm", 1) > 0, row["name"]
