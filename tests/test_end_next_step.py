"""#5560: at the end of a game each person reads in the chat what to do next (the recap book), a bot gets no line."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
from test_end_recap import ended  # noqa: E402


def lines(log, team):
    return [json.loads(c.split(" ", 2)[2]) for c in log if c.startswith(f"tellraw @a[team={team}] ")]


def test_the_person_reads_what_to_do_next_after_the_book():
    log, _, _ = ended()
    keys = [m.get("translate") for m in lines(log, "p1")]
    assert "aoe2mc.recap.next" in keys
    book = max(i for i, c in enumerate(log) if "hotbar.0" in c)
    assert log.index(next(c for c in log if "aoe2mc.recap.next" in c)) > book


def test_a_bot_gets_no_line():
    log, _, _ = ended()
    assert not any("aoe2mc.recap.next" in c and "team=p2" in c for c in log)
