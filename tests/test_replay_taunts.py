"""The live replay shows the AoE2 text of a taunt after its number (#2234, game/data/taunts.jsonl, AoE2 wiki "Taunt"):
"11" and "11 haha" are taunt 11; other chat lines stay as they are."""
import json

from test_replay import Fake, data

from game import replay


def chat(text):
    r = replay.Replay(Fake(), data([]))
    out = r.commands({"time": 0, "player": 2, "kind": "chat", "text": text})
    assert out[0].startswith("tellraw @a ")
    return json.loads(out[0][len("tellraw @a "):])[1]["text"]


def test_a_taunt_number_shows_its_text():
    assert chat("11") == f"11 ({replay.TAUNTS['11'].strip('()')})"
    assert chat("14") == f"14 ({replay.TAUNTS['14']})"
    assert chat("105") == f"105 ({replay.TAUNTS['105']})"


def test_a_taunt_with_text_after_the_number_is_that_taunt():
    assert chat("11 haha") == f"11 haha ({replay.TAUNTS['11'].strip('()')})"


def test_other_chat_lines_stay_as_they_are():
    after = str(max(map(int, replay.TAUNTS)) + 1)                    # a number after the last taunt
    for text in ("hello", "gl hf", after, "0", "11haha", "lol 11"):
        assert chat(text) == text
