"""Automerge merges a green PR from a claim ref `claim/*`, as a PR of `agent/*`, `claude/*` and `ccr-*`: PR #5972 came
from `claim/5942-2` and waited for the owner (#5988). The runs still never push to a claim ref (#5985)."""
import claim
import cycle_start
import ship_pr
import test_automerge_label as t

GREEN = [{"name": ship_pr.QUICK, "status": "completed", "conclusion": "success"}]


def test_a_claim_ref_is_an_agent_branch():
    assert claim.AGENT_BRANCH.match("claim/5942-2")
    assert all(claim.AGENT_BRANCH.match(p + "x") for p in cycle_start.AGENT)
    assert not claim.AGENT_BRANCH.match("owner/claim/5")


def test_automerge_takes_a_claim_ref_with_no_label():
    assert t.selected([t.pr("claim/5942-2"), t.pr("owner/w")]) == ["claim/5942-2"]


def test_a_green_claim_ref_pr_waits_for_automerge_not_the_owner():
    pr = {"number": 5972, "body": "Closes #5942", "labels": [], "head": {"ref": "claim/5942-2", "sha": "abc"}}
    assert claim.stuck_lines([(5942, "beat 40 min ago")], [pr], lambda sha: GREEN) == []
    pr["head"]["ref"] = "owner/w"
    assert "waits for the owner" in claim.stuck_lines([(5942, "beat 40 min ago")], [pr], lambda sha: GREEN)[0]
