"""A note in parentheses on a "Depends on:" line is no dependency: "(the epic #6001 closes when this ticket merges)"
made the ticket wait for its own epic, and the epic for the ticket, so the queue had no ready ticket for 20 hours."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "framework" / "tools"))
import dashboard  # noqa: E402


def test_note_in_parentheses_is_no_dependency():
    body = "Depends on: #6013 (the palette code of #6001; the epic #6001 waits only for #6016 and #6017)\n"
    assert dashboard.depends({"body": body}) == [6013]


def test_numbers_outside_the_note_stay():
    assert dashboard.depends({"body": "Depends on: #1 (a note #9), #2\n"}) == [1, 2]
