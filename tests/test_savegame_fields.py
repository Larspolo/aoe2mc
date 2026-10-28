"""Each field that a module of game/ sets on a Gather is in the saved game, or in savegame.NOT_SAVED with its reason
(#2535, epic #2253): a new field that a save loses fails here, in the PR that adds it, not in a later refill."""
import glob
import os
import re

from game import savegame

GAME = os.path.join(os.path.dirname(__file__), "..", "game")
SETS = (r"\bg\.(\w+)\s*(?:[-+*|&]?=)(?!=)",                           # g.x = ..., g.x += ...
        r"\bg\.(\w+)\s*,[^=\n]*=(?!=)",                                # g.x, g.y = ...
        r"setattr\(g,\s*\"(\w+)\"",
        r"vars\([gx]\)\.setdefault\(\"(\w+)\"",                     # x: a side of scenario.py (#3083)
        r"vars\(g\)\[\"(\w+)\"\]\s*=(?!=)")
ORDERS = {"farmers", "garrisons", "groups", "ships", "stances", "techs", "villagers"}   # savegame.orders, "techs"
GAPS = {                                                               # game state that the save loses: its ticket
}


def fields(text):
    """The names of the fields that the code text sets on a Gather g."""
    return {m[1] for p in SETS for m in re.finditer(p, text)}


def found():
    """Each field name that game/*.py sets on a Gather -> the files that set it."""
    names = {}
    for path in sorted(glob.glob(os.path.join(GAME, "*.py"))):
        with open(path, encoding="utf-8") as f:
            for n in fields(f.read()):
                names.setdefault(n, []).append(os.path.basename(path))
    return names


def saved():
    return set(savegame.FIELDS + savegame.PACKED + savegame.KEPT) | ORDERS


def test_the_scan_finds_a_new_field():
    assert fields("    g.new_field = 1\n    g.a, g.b = 0, 1\n    vars(g).setdefault(\"c\", {})\n    g.d += 2\n") \
        == {"new_field", "a", "b", "c", "d"}
    assert fields("    if g.aegis == 1:\n    x = g.stock\n") == set()


def test_each_field_of_a_gather_is_saved_or_has_a_reason():
    lost = {n: fs for n, fs in found().items() if n not in saved() | set(savegame.NOT_SAVED) | set(GAPS)}
    assert not lost, f"{lost}: save it in game/savegame.py or add it to NOT_SAVED with the reason"


def test_not_saved_has_no_saved_or_old_name():
    assert not set(savegame.NOT_SAVED) & saved()
    assert set(savegame.NOT_SAVED) <= set(found()), "a name of NOT_SAVED that no module of game/ sets: remove it"
    assert list(savegame.NOT_SAVED) == sorted(savegame.NOT_SAVED)


def test_a_gap_is_not_saved_and_not_in_not_saved():
    assert not set(GAPS) & (saved() | set(savegame.NOT_SAVED)), "a saved field: remove its line from GAPS"
