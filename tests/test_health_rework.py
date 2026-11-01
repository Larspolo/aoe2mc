"""framework/tools/health.py weak_spots (#5461): rework counts a bug ticket that names a PR merged before the bug, not
a PR that merged after it (the bug blocked that PR)."""
import datetime

import health

SINCE = datetime.datetime(2026, 10, 26, 0, 0, tzinfo=datetime.timezone.utc)


def test_a_pr_that_merged_after_the_bug_is_no_rework():
    bug = lambda n, body: {"number": n, "title": "Fix x", "body": body, "created_at": "2026-10-26T05:00:00Z",
                           "labels": [{"name": "bug"}]}
    issues = [bug(20, "Found after PR #11."), bug(21, "This test blocks PR #12.")]
    prs = [{"number": 11, "merged_at": "2026-10-26T02:00:00Z"}, {"number": 12, "merged_at": "2026-10-26T07:00:00Z"}]
    assert health.weak_spots(issues, [], prs, [], SINCE)["rework"] == 1
