"""The ticket lookup of Automerge (#4773): body, commits, claim of the branch, title, "Part of"."""
from framework.tools.pr_ticket import branch_claims, ticket


def test_body_closes():
    assert ticket("Closes #12", "Closes #9", "x (#7)", {}) == (12, False)


def test_commit_closes():
    assert ticket("no word", "Fix it\n\nfixes #9", "x", {}) == (9, True)


def test_claim_of_branch():
    tips = {5: "Claim #5 by claude/a (abc)", 6: "Beat #6 by claude/b", 8: "Release #8 by claude/a"}
    claims = branch_claims(tips, "claude/a")
    assert claims == {5: "Claim #5 by claude/a (abc)"}
    assert ticket("refs #4458", "Test it", "Test (#3)", claims) == (5, True)


def test_title():
    assert ticket("Closes nothing; refs #4458", "Test", "Test: x (#4458)", {}) == (4458, True)


def test_part_of_keeps_ticket_open():
    assert ticket("Part of #4", "Part of #4", "x (#4)", {4: "Claim #4 by b"}) == (None, False)


def test_none():
    assert ticket("", "", "x", {}) == (None, False)
