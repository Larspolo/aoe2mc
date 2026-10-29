"""tools/claim.py --review: the process review waits for merged PRs, never for hours (owner, 2026-10-29; #3465 had a
4-hour floor)."""
import claim

LAST = "2026-10-28T12:00:00Z"


def test_the_review_slot_counts_only_merged_prs():
    assert claim.pr_slot(LAST, 200, 199) is None                                     # too few PRs
    assert claim.pr_slot(LAST, 200, 200) == "200pr-20261028T120000Z-1"              # at once, at any time
    assert claim.pr_slot(None, 200, 200) == "200pr-none-1"                          # no review yet
