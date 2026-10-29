"""The pacer starts no refill run while a refill lock is younger than `refill_gap` minutes (2026-10-29: 16 of 30 deep
runs made no PR, most found the refill lock taken or nothing to refill)."""
import dashboard
import health
import pytest

import usage

NOW = 1_800_000_000
EPIC = {"number": 7, "labels": [{"name": "epic"}], "body": "", "created_at": "2027-01-15T08:00:00Z"}


def ref(key, minutes_ago):
    return f"{key} {NOW - minutes_ago * 60} Claim refill by run"


def test_a_young_refill_lock_counts():
    assert usage.refill_recent([ref("refill-0-202610290010", 10)], NOW, minutes=60)
    assert usage.refill_recent([ref("refill-936-74", 59)], NOW, minutes=60)


def test_an_old_lock_or_a_ticket_claim_does_not_count():
    assert not usage.refill_recent([ref("refill-0-202610282300", 61)], NOW, minutes=60)
    assert not usage.refill_recent([ref("3562", 1), ref("review-200pr-3400-1", 1)], NOW, minutes=60)
    assert not usage.refill_recent(None, NOW)                 # git could not read the refs


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(dashboard, "pages", lambda path: [EPIC])
    monkeypatch.setattr(dashboard, "api", lambda path: {"total_count": 0})
    monkeypatch.setattr(usage, "read_flow", lambda now: (None, "flow ok"))
    monkeypatch.setattr(usage, "due_reviews", lambda: [])
    monkeypatch.setattr(usage, "release_due", lambda: [])
    refs = []
    monkeypatch.setattr(health, "claim_refs", lambda remote="origin": refs)
    return refs


def fire():
    found = {"five_hour": (0.2, NOW + 3 * 3600, "allowed")}
    return usage.fire(found, NOW, status=([], ""))


def test_an_epic_check_starts_a_refill_run(fake):
    k, runs, line = fire()
    assert "refill 1 (epic check #7)" in line


def test_a_young_refill_lock_stops_the_refill_run(fake, monkeypatch):
    fake.append(ref("refill-0-202610290010", 20))
    monkeypatch.setattr(usage, "target_runs", lambda *a, **kw: 1)
    k, runs, line = fire()                                     # 0 ready >= 1 // 2
    assert "refill 0 (" in line and "refill lock" in line


def test_a_near_empty_queue_refills_also_after_a_young_lock(fake, monkeypatch):
    fake.append(ref("refill-0-202610290010", 20))
    monkeypatch.setattr(usage, "target_runs", lambda *a, **kw: 40)
    monkeypatch.setattr(usage, "free_sources", lambda: ["2 roadmap features with no epic"])
    k, runs, line = fire()                                     # 0 ready < 40 / 2
    assert "refill 1 (" in line
