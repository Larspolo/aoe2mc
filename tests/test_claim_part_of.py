"""claim.py --guard: a merged PR with `Part of #N` does not close ticket N (#4063): its prose said "It does not close
#4063", and the guard stopped each later PR of the ticket."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import claim  # noqa: E402


def pr(n, body, merged="2026-10-30T09:26:56Z"):
    return {"number": n, "head": {"ref": "run-0"}, "body": body, "state": "closed", "merged_at": merged}


def test_a_part_pr_that_says_it_does_not_close_the_ticket_is_no_stop():
    assert claim.other_pr([pr(1, "This PR fixes the crash. It does not close #22.\n\nPart of #22")], 22, "run-1") is None


def test_a_part_of_another_ticket_does_not_hide_a_close():
    assert claim.other_pr([pr(2, "Closes #22\n\nPart of #220")], 22, "run-1") == 2
