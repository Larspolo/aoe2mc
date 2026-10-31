"""A long trigger instruction also goes to the chat, which wraps it (#5298)."""
import json

import aoe2mc


def lines(msg):
    return aoe2mc.instruction_lines(dict(message=msg, time=4, player=1), None)


def test_long_instruction_goes_to_chat():
    msg = "x" * (aoe2mc.SUBTITLE_CHARS + 1)
    out = lines(msg)
    chat = [c for c in out if c.startswith("tellraw @a ")]
    assert len(chat) == 1 and json.loads(chat[0][len("tellraw @a "):])["text"] == msg
    assert any(c.startswith("title @a subtitle ") for c in out)


def test_short_instruction_has_no_chat():
    assert not [c for c in lines("x" * aoe2mc.SUBTITLE_CHARS) if c.startswith("tellraw")]
