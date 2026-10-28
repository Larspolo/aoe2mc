"""MAP of tools/triggers.py keeps its lines in alphabetical order: each trigger ticket adds one line, and lines added at
the end conflicted in 8 of 13 conflicted PRs (process review, 2026-10-28)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import triggers  # noqa: E402


def test_the_lines_of_map_are_in_alphabetical_order():
    keys = list(triggers.MAP)
    assert keys == sorted(keys), "put each new line of MAP in alphabetical order, not at the end"
