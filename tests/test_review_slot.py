"""The process review and the roadmap review start after a count of merged PRs (#898, #2039): `claim.py 0 --review`,
`--reviewed`, `--roadmap`."""
from test_claim import clones, tool  # noqa: F401
from test_claim_refill import deep

import claim

T = 1793000000                                                                  # 2026-10-26 07:33:20 UTC
BODY = 'Dashboard\n<!-- agent-state: {"last_run": "2026-10-26T07:00:00Z", "runs": 150, "review_minutes": 90} -->\n' \
       '### Process changes\n'


def test_the_review_lock_wins_once(clones):                                    # noqa: F811
    a, b, _ = clones
    deep(clones)
    assert tool(a, "0", "--review").returncode == 0                             # a local remote: no state, no count
    assert tool(b, "0", "--review").returncode == 1                             # the same review
    assert tool(a, "0", "--roadmap").returncode == 0 and tool(b, "0", "--roadmap").returncode == 1


def test_a_review_waits_for_its_gap_of_merged_prs():
    last = "2026-10-26T07:00:00Z"
    assert claim.pr_slot(last, 50, 49) is None
    assert claim.pr_slot(last, 50, 50) == claim.pr_slot(last, 50, 99) == "50pr-20261026T070000Z-1"
    assert claim.pr_slot(last, 50, 100) == "50pr-20261026T070000Z-2"            # a review that no run finished
    assert claim.pr_slot(None, 100, 100) == "100pr-none-1"
    assert claim.pr_slot("2026-10-26T09:00:00Z", 50, 50) != claim.pr_slot(last, 50, 50)   # the next review


def test_no_change_doubles_the_gap_and_a_change_resets_it():
    body = claim.reviewed(BODY, False, T)
    state = claim.agent_state(body)
    assert state == {"last_run": "2026-10-26T07:00:00Z", "runs": 150, "last_review": "2026-10-26T07:33:20Z",
                     "review_prs": 100}                                         # review_minutes goes
    assert body.startswith("Dashboard\n<!-- agent-state: ") and body.endswith("### Process changes\n")
    for want in (200, 200):                                                    # REVIEW_MAX (#1697)
        body = claim.reviewed(body, False, T)
        assert claim.agent_state(body)["review_prs"] == want
    assert claim.agent_state(claim.reviewed(body, True, T))["review_prs"] == 50


def test_the_merged_prs_without_github_start_the_review():
    assert claim.merged_since(None, 50) == 50
    assert claim.merged_since("2026-10-26T07:00:00Z", 100, "nowhere") == 100     # not a GitHub remote
