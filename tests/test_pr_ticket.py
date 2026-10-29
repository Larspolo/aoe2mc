"""An agent PR whose body has no closing line gets its ticket from the claim beat of its branch (#4122)."""
import datetime

import cycle_start as start

NOW = datetime.datetime(2026, 10, 29, 12, 0, tzinfo=datetime.timezone.utc)
PR = {"number": 4061, "head": {"ref": "claude/x-cx"}, "body": "## What changed\nNo closing line.",
      "created_at": "2026-10-29T11:00:00Z", "labels": [{"name": "conflict"}]}
HELD = {3908: (40, "Beat #3908 by claude/other"), 3909: (5, "Beat #3909 by claude/x-cx")}


def test_the_ticket_comes_from_the_body_first_then_from_the_beat_of_the_branch():
    assert start.pr_ticket({**PR, "body": "Closes #12"}, HELD) == 12
    assert start.pr_ticket(PR, HELD) == 3909
    assert start.pr_ticket({**PR, "head": {"ref": "claude/none"}}, HELD) is None


def test_a_pr_with_no_closing_line_and_a_live_beat_is_left_to_its_run():
    issues = {3909: {"number": 3909, "labels": [{"name": "in-progress"}]}}
    w = start.pr_work(PR, issues, [], HELD[3909], NOW, ticket=start.pr_ticket(PR, HELD))
    assert "leave it" in w and "claude/x-cx" in w
