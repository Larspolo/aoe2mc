"""The replay texts are translate components with the English fallback of game/data/texts.jsonl (#5375)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))

import lang  # noqa: E402
import replay  # noqa: E402
import replay_input  # noqa: E402


def keys(c):
    """All translate keys in a component (also in "with" and "extra")."""
    if isinstance(c, list):
        return [k for x in c for k in keys(x)]
    if not isinstance(c, dict):
        return []
    return ([c["translate"]] if "translate" in c else []) + keys(c.get("with", [])) + keys(c.get("extra", []))


def check(c):
    found = keys(c)
    assert found
    for k in found:
        assert k in lang.EN_US


def test_end_title_is_translate():
    titles = [json.loads(c.split(" ", 3)[3]) for c in replay.Replay.end_commands(65000) if not c.startswith(("title @a times", "playsound"))]
    for t in titles:
        check(t)
    sub = next(t for t in titles if "time" in t["translate"])
    assert sub["fallback"] == lang.EN_US[sub["translate"]] and sub["with"] == ["01:05"]


def test_say_fallback_is_table():
    c = replay.say("resigns", "Ann", color="red")
    assert c["fallback"] == lang.EN_US["aoe2mc.replay.resigns"] and c["color"] == "red"
    assert lang.plain(c) == lang.EN_US["aoe2mc.replay.resigns"].replace("%s", "Ann")


def test_input_lines_are_translate():
    check(json.loads(replay_input.help_head()))
    lines = replay_input.fight_lines([{"start": 0, "players": [1, 2], "units": 9}], {1: ("A", "red"), 2: ("B", "blue")})
    for line in lines:
        check(json.loads(line.split(" ", 2)[2]))
