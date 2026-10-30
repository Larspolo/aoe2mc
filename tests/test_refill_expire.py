"""framework/tools/claim.py --refill: the lock of a ticket with no sub-issue expires with the 10-minute slot (#855)."""
import claim

T = 1793000000                                                      # 2026-10-26 07:33 UTC


def state(monkeypatch, summary, now=T):
    monkeypatch.setattr(claim, "on_github", lambda remote="origin": True)
    monkeypatch.setattr(claim, "api", lambda path: {"number": 397, "sub_issues_summary": summary})
    return claim.refill_state(397, now=now)


def test_no_sub_issue_locks_the_slot(monkeypatch):
    none = {"completed": 0, "percent_completed": 0, "total": 0}
    assert state(monkeypatch, none) == "0-20261026073"
    assert state(monkeypatch, none, T + 60) == state(monkeypatch, none)          # 07:34: the same lock
    assert state(monkeypatch, none, T + 900) == "0-20261026074"                 # 07:48: a new lock
    assert state(monkeypatch, None) == "0-20261026073"                          # no summary: as no sub-issue


def test_sub_issues_lock_the_closed_count(monkeypatch):
    assert state(monkeypatch, {"completed": 0, "total": 3}) == "0"
    assert state(monkeypatch, {"completed": 2, "total": 3}, T + 3600) == "2"
