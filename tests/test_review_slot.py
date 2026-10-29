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


def test_a_change_halves_the_gap_and_no_change_resets_or_doubles_it(monkeypatch):
    for name, value in (("REVIEW", 80), ("REVIEW_MIN", 10), ("REVIEW_MAX", 512)):   # test values (owner, 2026-10-29)
        monkeypatch.setattr(claim, name, value)
    body = claim.reviewed(BODY, True, T)
    state = claim.agent_state(body)
    assert state == {"last_run": "2026-10-26T07:00:00Z", "runs": 150, "last_review": "2026-10-26T07:33:20Z",
                     "review_prs": 40}                                          # review_minutes goes
    assert body.startswith("Dashboard\n<!-- agent-state: ") and body.endswith("### Process changes\n")
    gaps = []
    for changed in (True, True, True, False, False, False, False, False, True):
        body = claim.reviewed(body, changed, T)
        gaps.append(claim.agent_state(body)["review_prs"])
    assert gaps == [20, 10, 10, 80, 160, 320, 512, 512, 256]


def test_a_gap_of_an_earlier_rule_counts_as_the_first_gap(monkeypatch):
    for name, value in (("REVIEW", 80), ("REVIEW_MIN", 10), ("REVIEW_MAX", 512)):
        monkeypatch.setattr(claim, name, value)
    assert claim.review_gap({"review_prs": 200}) == claim.review_gap({}) == 80     # 200 and 800: the rules before
    assert claim.review_gap({"review_prs": 10}) == 10 and claim.review_gap({"review_prs": 256}) == 256


def test_the_merged_prs_without_github_start_the_review():
    assert claim.merged_since(None, 50) == 50
    assert claim.merged_since("2026-10-26T07:00:00Z", 100, "nowhere") == 100     # not a GitHub remote
