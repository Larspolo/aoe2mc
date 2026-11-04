"""data/achievement_keys.jsonl (#5781): one line per optional key of data/achievements.jsonl, with its type, what it
does and its issue. A new key of an achievement is a new line there, not a change of a shared table of a test. The
fields of a Gather that the achievements keep go into a saved game by achievements.field, not by a line of savegame.py."""
import json
import os
import sys

import pytest
from test_achievements import TYPES, test_each_line_has_the_form_and_a_known_parent

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import achievements  # noqa: E402
import savegame  # noqa: E402

SAMPLE = {"float": 0.5, "int": 1, "list": [], "number": 1, "str": "s"}   # a value of each type
ROW = {"name": "TEST", "title": "T", "description": "D", "icon": "minecraft:stone", "parent": "root", "event": "x"}


def rows():
    path = os.path.join(os.path.dirname(aoe2mc.__file__), "data", "achievement_keys.jsonl")
    return [json.loads(s) for s in open(path, encoding="utf-8")]


def test_each_key_has_a_known_type_a_text_and_an_issue():
    names = [r["name"] for r in rows()]
    assert len(names) == len(set(names))
    for r in rows():
        assert set(r) == {"name", "type", "text", "issue"} and r["type"] in TYPES and r["text"] and r["issue"] > 0, r


@pytest.mark.parametrize("bad", ["no line", "wrong type"])
def test_a_key_with_no_line_or_of_the_wrong_type_fails_and_a_key_of_the_file_passes(monkeypatch, bad):
    key = rows()[0]
    monkeypatch.setattr(aoe2mc, "ACHIEVEMENTS", [{**ROW, key["name"]: SAMPLE[key["type"]]}])
    test_each_line_has_the_form_and_a_known_parent()
    monkeypatch.setattr(aoe2mc, "ACHIEVEMENTS", [{**ROW, **({"new_key": 1} if bad == "no line" else {key["name"]: {}})}])
    with pytest.raises(AssertionError):
        test_each_line_has_the_form_and_a_known_parent()


def test_the_saved_fields_of_the_achievements_are_kept():
    assert achievements.SAVED and set(achievements.SAVED) <= set(savegame.KEPT)
    assert len(achievements.SAVED) == len(set(achievements.SAVED))
