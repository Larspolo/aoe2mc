"""tools/claim.py --review: the process review waits for 200 merged PRs and 4 hours after the last one (#3465)."""
import datetime

import claim

LAST = "2026-10-28T12:00:00Z"
T0 = datetime.datetime(2026, 10, 28, 12, tzinfo=datetime.timezone.utc).timestamp()


def test_no_review_slot_before_200_prs_or_before_4_hours():
    assert claim.REVIEW == 200 and claim.REVIEW_HOURS == 4
    assert claim.pr_slot(LAST, 200, 199, 4, T0 + 5 * 3600) is None                   # too few PRs
    assert claim.pr_slot(LAST, 200, 400, 4, T0 + 3.9 * 3600) is None                 # too early
    assert claim.pr_slot(LAST, 200, 200, 4, T0 + 4 * 3600) == "200pr-20261028T120000Z-1"
    assert claim.pr_slot(None, 200, 200, 4, T0) == "200pr-none-1"                    # no review yet
    assert claim.pr_slot(LAST, 100, 100, 0, T0) == "100pr-20261028T120000Z-1"        # the roadmap: no hours

