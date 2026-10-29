"""The 9 AoE2 DE "Art of War" challenges (#3761, epic #3759): game/data/challenges.jsonl has the civilization, the goal,
the unlock order ("after") and the medal limits of each one (AoE2 wiki, one page per challenge). A limit is the largest
value that still gets the medal: game seconds of a "time" challenge, units lost of a "lost" challenge (the wiki "less
than 6 units lost" is a silver limit of 5). No setting and no game logic yet: they wait for decision #3760."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table  # noqa: E402

CHALLENGES = {r["name"]: r for r in table.load("challenges.jsonl")}
MEDALS = ("gold", "silver", "bronze")
UNITS = {"lost": "units lost", "time": "game seconds"}             # the value of each kind of challenge


def medal(name, value):
    """The medal of challenge `name` for `value` (game seconds or units lost: less is better), else None."""
    c = CHALLENGES[name]
    return next((m for m in MEDALS if value <= c[m]), None)


def limits(name):
    """The medal limits of challenge `name` as text, for example "gold 480, silver 600, bronze 780 game seconds"."""
    c = CHALLENGES[name]
    return ", ".join(f"{m} {c[m]}" for m in MEDALS) + f" {UNITS[c['medal']]}"
