"""game/data/music.jsonl: the tune of a game event (age_up, victory, defeat), category music (#5339)."""
import mcvalid

from . import form


def check(row):
    form(row, {"name": str, "sound": str, "pitch": float})
    assert mcvalid.sound_error(row["sound"]) is None, row
