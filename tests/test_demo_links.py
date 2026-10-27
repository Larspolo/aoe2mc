"""The issue links in the chat lines of an owner demo (game/demo_watch.py --say, the `demo` skill)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import demo_watch  # noqa: E402


def test_each_issue_number_of_a_demo_line_is_a_link():
    parts = demo_watch.chat("Ticket #1786: draw the box. See #12.", "Larspolo/aoe2mc")
    assert [p["text"] for p in parts] == ["[demo] ", "Ticket ", "#1786", ": draw the box. See ", "#12", "."]
    assert parts[2]["click_event"] == {"action": "open_url", "url": "https://github.com/Larspolo/aoe2mc/issues/1786"}
    assert parts[4]["click_event"]["url"].endswith("/issues/12")
    assert "click_event" not in parts[1] and parts[1]["color"] == "gold"
