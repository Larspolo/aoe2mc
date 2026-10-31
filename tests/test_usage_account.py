"""A run's own `usage.py --fire` counts only the claims of its own account (#4238)."""
import time

import dashboard
import health
import pytest
import usage

NOW = int(time.time())


@pytest.fixture
def fake(monkeypatch):
    for name, fn in [("pages", lambda path: []), ("api", lambda path: {"total_count": 0})]:
        monkeypatch.setattr(dashboard, name, fn)
    monkeypatch.setattr(usage, "read_flow", lambda now: (None, "flow ok"))
    monkeypatch.setattr(usage, "due_reviews", lambda **_: [])
    monkeypatch.setattr(usage, "release_due", lambda: [])
    monkeypatch.setattr(usage, "free_sources", lambda: [])
    monkeypatch.setattr(usage, "target_runs", lambda *a, **kw: 40)
    monkeypatch.setattr(health, "first_account", lambda config=None: "a")
    refs = []
    monkeypatch.setattr(health, "claim_refs", lambda remote="origin": refs)
    return refs


def claims(line):
    return int(line.split(" · claims ")[1].split(" ")[0])


def fire(**kw):
    return usage.fire({"five_hour": (0.2, NOW + 3 * 3600, "allowed")}, NOW, status=([], ""), **kw)


def test_a_run_of_account_b_counts_only_the_claims_of_b(fake):
    fake += [f"10 {NOW - 60} Claim #10 by claude/a (x1) account a lane haiku",
             f"11 {NOW - 60} Claim #11 by claude/b (x2)",                       # no account word: the first account
             f"12 {NOW - 60} Claim #12 by claude/c (x3) account b",
             f"13 {NOW - 60} Claim #13 by claude/d (x4) account b lane deep"]
    assert claims(fire(account="b")[2]) == 2
    assert claims(fire(account="a")[2]) == 2
    assert claims(fire()[2]) == 4


def test_no_account_words_count_as_today(fake):
    fake += [f"10 {NOW - 60} Claim #10 by claude/a (x1)", f"11 {NOW - 60} Beat #11 by claude/b lane haiku"]
    assert claims(fire()[2]) == 2
    assert health.count_lanes(fake, health.datetime.datetime.now(health.datetime.timezone.utc)) == {"opus": 1, "haiku": 1}
