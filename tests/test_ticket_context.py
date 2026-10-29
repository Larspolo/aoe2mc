"""tools/ticket_context.py prints the code places of a ticket body in one call (#3829)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import ticket_context  # noqa: E402


def test_a_body_gives_the_def_block_the_file_and_the_missing_name():
    out = ticket_context.context("Use `dashboard.names()` in `tools/dashboard.py`, not `no_such_function_here()`.")
    assert "tools/dashboard.py:" in out and "def names(text):" in out and "return out - NO_OVERLAP" in out
    assert "tools/dashboard.py: " in out and "Build the dashboard" in out                   # the path, lines, docstring
    assert "not found: no_such_function_here()" in out


def test_a_path_selects_one_file_of_a_base_name_and_a_test_file_gives_its_tests():
    out = ticket_context.context("See `.claude/skills/autopilot/SKILL.md` and `tests/test_ticket_context.py`.")
    assert ".claude/skills/autopilot/SKILL.md" in out and "skills/verify/SKILL.md" not in out
    assert "test_a_body_gives_the_def_block_the_file_and_the_missing_name" in out


def test_a_def_block_stops_at_the_line_limit():
    assert len(ticket_context.defs("context", ["tools/ticket_context.py"], lines=3)[0].splitlines()) == 4
