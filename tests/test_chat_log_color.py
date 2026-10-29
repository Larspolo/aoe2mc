"""The chat lines of the server log with the name in its team color (#3681): the game program still reads them (#3889)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "game"))
import play_guide  # noqa: E402
import watch  # noqa: E402


@pytest.mark.parametrize("chat", [play_guide.CHAT, watch.CHAT])
@pytest.mark.parametrize("line", ["[12:02:32 INFO]: [Not Secure] <\x1b[94maoe2mc\x1b[0m> hello color",   # from a real server
                                  "[12:02:32 INFO]: [Not Secure] <aoe2mc> hello color",                 # no TERM, no team
                                  "[12:02:32 INFO]: <aoe2mc> hello color"])
def test_a_chat_line_gives_the_name_and_the_text(chat, line):
    assert chat.search(line).groups() == ("aoe2mc", "hello color")


def test_a_system_line_is_no_chat():
    assert not play_guide.CHAT.search("[12:02:13 INFO]: System chat: \x1b[93maoe2mc joined the game\x1b[0m")
