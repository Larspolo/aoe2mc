"""tools/cycle_start.py: no ready candidate gives no Claim line and no IndexError (#4204)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import cycle_start  # noqa: E402


def test_no_candidate_no_claim_line():
    assert cycle_start.claim_line([]) == []


def test_claim_line_of_the_candidates():
    assert cycle_start.claim_line([{"number": 7}]) == ["Claim: python3 tools/claim.py 7"]
    assert cycle_start.claim_line([{"number": n} for n in range(1, 8)]) == ["Claim: python3 tools/claim.py 1 --or 2 3 4 5"]
