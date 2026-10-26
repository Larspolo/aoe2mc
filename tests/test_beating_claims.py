"""The pacer counts the runs by their claim beats, not by issue changes (#635)."""
import datetime

import health
import usage

NOW = datetime.datetime(2026, 10, 26, 8, 15, tzinfo=datetime.timezone.utc)
T = int(NOW.timestamp())


def test_count_the_top_slot_with_a_recent_beat():
    lines = [f"601 {T - 300} Beat #601 by claude/a",              # beat 5 minutes ago: works
             f"602 {T - 3600} Claim #602 by claude/b",            # silent for an hour: stopped
             f"603 {T - 600} Release #603 by claude/c",           # released: does not work
             f"604 {T - 3600} Claim #604 by claude/d",            # slot 1 old ...
             f"604-2 {T - 60} Claim #604 by claude/e",            # ... slot 2 new: a takeover works
             f"comment-99 {T} Claim comment 99", f"refill-0-20261026080 {T} Claim refill"]   # locks, not runs
    assert health.count_beating(lines, NOW) == 2


def test_the_usage_line_has_runs_and_old_claims_lines_do_not_count():
    line = usage.sample_line({"five_hour": (0.3, T + 3600, "allowed")}, T, 7)
    assert line.endswith("· runs 7")
    assert health.samples([{"body": line}])[0][3] == 7
    old = "Usage: 2026-10-26T08:00:00Z · usage 30.0% · resets 2026-10-26T11:30:00Z · claims 2"
    assert health.samples([{"body": old}]) == []
