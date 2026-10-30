"""claim.py --guard: a merged PR does not stop the guard while its ticket is open on GitHub (#4063): no merged PR closed
it. The body of #4633 quoted "does not close #4063" and had `Part of #4063` only in a code span."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import claim  # noqa: E402

BODY = 'Its prose "It does not close #22" matched. `Part of #22`'


def pr(state="closed", merged="2026-10-30T09:53:06Z"):
    return {"number": 7, "head": {"ref": "run-0"}, "body": BODY, "state": state, "merged_at": merged}


def test_a_merged_pr_of_an_open_ticket_is_no_stop():
    assert claim.other_pr([pr()], 22, "run-1", still_open=True) is None


def test_an_open_pr_still_stops():
    assert claim.other_pr([pr("open", None)], 22, "run-1", still_open=True) == 7


def test_with_no_ticket_state_a_merged_pr_stops():
    assert claim.other_pr([pr()], 22, "run-1") == 7
