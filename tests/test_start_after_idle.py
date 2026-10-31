"""A "Start after: N PRs after #M" wait ends after claim.ROADMAP_IDLE minutes with no merged PR (#5201)."""
import datetime

import claim
import dashboard

NOW = datetime.datetime(2026, 10, 31, 18, 0, tzinfo=datetime.timezone.utc)
ISSUE = {"number": 7, "body": "Start after: 5 PRs after #100"}


def waits(minutes, merged=2):
    return dashboard.waits(ISSUE, after=lambda m: merged, now=NOW,
                           last=lambda: NOW - datetime.timedelta(minutes=minutes))


def test_the_wait_holds_with_a_recent_merge_and_ends_after_an_idle_hour():
    assert waits(5) and waits(claim.ROADMAP_IDLE - 1)
    assert not waits(claim.ROADMAP_IDLE + 1)


def test_the_count_still_ends_the_wait_and_a_ticket_with_no_line_never_waits():
    assert not waits(5, merged=5)
    assert not dashboard.waits({"number": 8, "body": ""}, after=lambda m: 0, now=NOW, last=lambda: NOW)
