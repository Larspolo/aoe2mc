"""The roadmap review is due after ROADMAP_EARLY merged PRs, not ROADMAP, while the refill has no source: fewer tickets
ready than the target runs, and each roadmap feature has an epic (#3741)."""
import claim
import usage

LAST = "2026-10-29T08:33:28Z"
BODY = f'<!-- agent-state: {{"last_roadmap": "{LAST}"}} -->\n'


def slot(monkeypatch, merged, starved):
    monkeypatch.setattr(claim, "on_github", lambda remote="origin": True)
    monkeypatch.setattr(claim, "api", lambda path: {"body": BODY})
    monkeypatch.setattr(claim, "last_lock", lambda kind, remote="origin": None)
    monkeypatch.setattr(claim, "merged_since", lambda last, gap, remote="origin": merged)
    monkeypatch.setattr(claim, "idle_minutes", lambda last, remote="origin": 0)   # no merge read: tests/test_roadmap_idle.py
    asked = []
    key, gap = claim.review_slot("roadmap", starved=lambda: asked.append(1) or starved)
    return key, gap, bool(asked)


def test_a_starved_refill_makes_the_roadmap_review_due_after_30_prs(monkeypatch):
    assert slot(monkeypatch, 31, True) == ("30pr-20261029T083328Z-1", 30, True)
    assert slot(monkeypatch, 29, True) == (None, 100, False)           # below the early gap: no quota read


def test_a_refill_with_a_source_waits_for_100_prs(monkeypatch):
    assert slot(monkeypatch, 31, False) == (None, 100, True)
    assert slot(monkeypatch, 100, False) == ("100pr-20261029T083328Z-1", 100, False)


def test_the_process_review_keeps_its_gap(monkeypatch):
    monkeypatch.setattr(claim, "on_github", lambda remote="origin": True)
    monkeypatch.setattr(claim, "api", lambda path: {"body": BODY})
    monkeypatch.setattr(claim, "merged_since", lambda last, gap, remote="origin": 31)
    assert claim.review_slot("review", starved=lambda: True)[0] is None


def test_starved_needs_r_below_n_and_no_source(monkeypatch):
    monkeypatch.setattr(usage, "read_usage", lambda: {"five_hour": (0.1, 0, "allowed")})
    monkeypatch.setattr(usage, "read_status", lambda: ([], ""))
    monkeypatch.setattr(usage, "burns", lambda comments, burn=None: (0.01, None))
    monkeypatch.setattr(usage, "release_due", lambda: [])
    import dashboard
    monkeypatch.setattr(dashboard, "pages", lambda path: [])
    for ready, target, free, want in ((11, 40, [], True), (11, 40, ["1 roadmap features with no epic"], False),
                                      (40, 40, [], False), (11, None, [], False)):
        monkeypatch.setattr(dashboard, "candidates", lambda issues, reserved=(), n=ready: [{}] * n)
        monkeypatch.setattr(usage, "target_runs", lambda *a, t=target, **k: t)
        monkeypatch.setattr(usage, "free_sources", lambda f=free: f)
        assert claim.refill_starved() is want, (ready, target, free)


def test_a_read_error_is_not_starved(monkeypatch):
    monkeypatch.setattr(usage, "read_usage", lambda: 1 / 0)
    assert claim.refill_starved() is False


def test_the_pacer_gives_its_own_ready_and_target_to_the_roadmap_slot(monkeypatch):
    seen = {}
    monkeypatch.setattr(claim, "review_slot", lambda kind, remote="origin", starved=None: seen.update({kind: starved()})
                        or (None, 100))
    monkeypatch.setattr(usage, "free_sources", lambda: [])
    assert usage.refill_need(11, 40, [], reviews=lambda: usage.due_reviews(starved=lambda: 11 < 40 and not usage.free_sources())) == ""
    assert seen == {"review": True, "roadmap": True}
