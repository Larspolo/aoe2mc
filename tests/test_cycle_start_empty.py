"""tools/cycle_start.py with no candidate: no claim line, no crash (a deep run with no lane:deep ticket)."""
import cycle_start as start


def test_no_candidate_gives_no_claim_line():
    assert start.claim_lines([]) == []
    assert start.claim_lines([{"number": 5}]) == ["Claim: python3 tools/claim.py 5"]
    assert start.claim_lines([{"number": 5}, {"number": 6}]) == ["Claim: python3 tools/claim.py 5 --or 6"]
