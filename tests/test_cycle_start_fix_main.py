"""tools/cycle_start.py names a "Fix main" ticket that closed after the red run (owner, #3225)."""
import cycle_start as start

RED_AT = "2026-10-28T09:36"


def issue(number, title, closed_at):
    return {"number": number, "title": title, "closed_at": closed_at}


def test_a_fix_main_ticket_closed_after_the_red_run_is_named():
    closed = [issue(3212, "Fix main: elevation damage test fails on the night CI run", "2026-10-28T19:35:12Z")]
    assert start.fixed_after(closed, RED_AT) == ["#3212 Fix main: elevation damage test fails on the night CI run"]


def test_a_fix_main_ticket_closed_before_the_red_run_is_not_named():
    closed = [issue(3100, "Fix main: old failure", "2026-10-27T08:00:00Z")]
    assert start.fixed_after(closed, RED_AT) == []


def test_another_closed_ticket_is_not_named():
    closed = [issue(3200, "Add a test of the menu", "2026-10-28T19:00:00Z")]
    assert start.fixed_after(closed, RED_AT) == []
