"""framework/tools/health.py milestone_per_week (#5552): the closed issues of a release milestone per 1 % of 7-day
quota, because the release bar stays at its level while the runs work only on the release focus."""
import datetime

import health

T = lambda h: datetime.datetime(2026, 11, 1, h, 0, tzinfo=datetime.timezone.utc)
POINTS = [(T(1), 60.0, 98.1), (T(3), 61.0, 98.1), (T(5), 62.5, 98.1)]   # weekly(): 2.5 % used


def issue(n, closed, title="v0.1.0", reason="completed", pr=False):
    i = {"number": n, "state": "closed", "closed_at": closed, "state_reason": reason,
         "milestone": {"title": title} if title else None}
    return {**i, "pull_request": {}} if pr else i


def test_it_counts_the_closed_issues_of_a_release_milestone_in_the_period():
    issues = [issue(1, "2026-11-01T02:00:00Z"), issue(2, "2026-11-01T04:30:00Z"),
              issue(3, "2026-11-01T00:30:00Z"),                         # before the first point
              issue(4, "2026-11-01T02:00:00Z", reason="not_planned"),
              issue(5, "2026-11-01T02:00:00Z", pr=True),
              issue(6, "2026-11-01T02:00:00Z", title=None),
              issue(7, "2026-11-01T02:00:00Z", title="Backlog"),
              {"number": 8, "state": "open", "closed_at": None, "milestone": {"title": "v0.1.0"}}]
    rate, n, used, names = health.milestone_per_week(issues, POINTS)
    assert (n, used, names) == (2, 2.5, ["v0.1.0"])
    assert rate == 2 / 2.5


def test_no_quota_or_one_point_gives_none():
    assert health.milestone_per_week([issue(1, "2026-11-01T02:00:00Z")], POINTS[:1]) is None
    flat = [(T(1), 60.0, None), (T(3), 60.0, None)]
    assert health.milestone_per_week([issue(1, "2026-11-01T02:00:00Z")], flat) is None
