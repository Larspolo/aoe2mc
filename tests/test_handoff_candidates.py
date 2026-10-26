"""A ticket with an open hand-off PR (label ready-to-merge) is no candidate and no claim (#546), with fixed data."""
import claim
import dashboard
from test_claim import clones  # noqa: F401  (fixture)


def issue(n, *names, body="", **kw):
    return dict(number=n, title=f"Ticket {n}", labels=[{"name": x} for x in names], body=body, **kw)


def pull(n, body, *names, state="open", ref="run-9"):
    return {"number": n, "head": {"ref": ref}, "body": body, "state": state, "labels": [{"name": x} for x in names],
            "updated_at": "2026-10-26T04:00:00Z"}


def test_candidates_skip_handoff():
    issues = [issue(4, "P3"), issue(5, "P3"), issue(6, "P3"), issue(7, "P3"),
              issue(40, "ready-to-merge", body="Furnish it.\n\nCloses #4", pull_request={}),
              issue(41, body="Closes #5", pull_request={}),                    # no hand-off: its run merges it
              issue(42, "ready-to-merge", body="Part of #6", pull_request={})]  # closes nothing
    assert [i["number"] for i in dashboard.candidates(issues)] == [5, 6, 7]


def test_handoff_pr():
    assert claim.handoff_pr([pull(40, "Closes #4", "ready-to-merge")], 4) == 40
    assert claim.handoff_pr([pull(40, "Closes #4")], 4) is None
    assert claim.handoff_pr([pull(40, "Closes #4", "ready-to-merge", state="closed")], 4) is None
    assert claim.handoff_pr([pull(40, "`Closes #4`", "ready-to-merge")], 4) is None   # no keyword in code
    assert claim.handoff_pr([pull(40, "Closes #44", "ready-to-merge")], 4) is None


def test_claim_refuses_handoff(clones, monkeypatch, capsys):  # noqa: F811
    a, _, _ = clones
    pulls = [pull(538, "Closes #12", "ready-to-merge", ref="run-0")]   # also the own branch: it waits for the owner
    monkeypatch.setattr(claim, "on_github", lambda remote="origin": True)
    monkeypatch.setattr(claim, "api", lambda path: pulls if path.startswith("pulls") else [])
    monkeypatch.chdir(a)
    assert claim.main(["12"]) == 1 and claim.refs(12) == {}
    assert "#538" in capsys.readouterr().out
    assert claim.main(["13"]) == 0
