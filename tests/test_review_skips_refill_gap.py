"""A due review starts its deep run also while a refill lock is younger than `refill_gap` (owner, 2026-10-29): the
review lock lets one run take it, so the gap of the refill runs must not delay it."""
import usage
from test_refill_gap import fake, fire, ref  # noqa: F401


def test_a_due_review_skips_the_refill_gap(fake, monkeypatch):  # noqa: F811
    fake.append(ref("refill-0-202610290010", usage.REFILL_GAP // 2))
    monkeypatch.setattr(usage, "target_runs", lambda *a, **kw: 1)
    asked = []
    monkeypatch.setattr(usage, "due_reviews", lambda **_: asked.append(1) or ["process review"])
    k, runs, line = fire()                                     # the epic check comes first, then the gap: 1 run
    assert "refill 1 (process review due)" in line and asked == [1]


def test_without_a_due_review_the_refill_gap_holds(fake, monkeypatch):  # noqa: F811
    fake.append(ref("refill-0-202610290010", usage.REFILL_GAP // 2))
    monkeypatch.setattr(usage, "target_runs", lambda *a, **kw: 1)
    k, runs, line = fire()
    assert "refill 0 (" in line
