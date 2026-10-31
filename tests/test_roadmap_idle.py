"""While the refill has no source, the roadmap review is due also below ROADMAP_EARLY merged PRs after ROADMAP_IDLE
minutes with no merged PR: with no ready ticket no run merges a PR, so the count alone never reaches the gap. On
2026-10-31 the queue stopped at 27 of 30 merged PRs, with 0 runs at a target of 36."""
import datetime

import claim

LAST = "2026-10-31T12:33:58Z"
BODY = f'<!-- agent-state: {{"last_roadmap": "{LAST}"}} -->\n'
T0 = datetime.datetime.fromisoformat(LAST.replace("Z", "+00:00")).timestamp()


def slot(monkeypatch, merges, minutes, starved=True):
    """review_slot("roadmap") `minutes` after LAST, with PRs merged `merges` minutes after LAST (newest first)."""
    monkeypatch.setattr(claim, "on_github", lambda remote="origin": True)
    monkeypatch.setattr(claim, "api", lambda path: {"body": BODY})
    monkeypatch.setattr(claim, "last_lock", lambda kind, remote="origin": None)
    rows = [(datetime.datetime.fromtimestamp(T0 + m * 60, datetime.timezone.utc), 5000 + k, "") for k, m in enumerate(merges)]
    monkeypatch.setattr(claim, "merge_rows", lambda last: rows if last == LAST else [])
    monkeypatch.setattr(claim.time, "time", lambda: T0 + minutes * 60)
    asked = []
    key, gap = claim.review_slot("roadmap", starved=lambda: asked.append(1) or starved)
    return key, gap, bool(asked)


def test_an_idle_hour_makes_the_review_due_at_the_merged_count(monkeypatch):
    merges = list(range(89, 62, -1))                                   # 27 PRs, the newest 89 minutes after LAST
    assert slot(monkeypatch, merges, 89 + claim.ROADMAP_IDLE) == ("27pr-20261031T123358Z-1", 27, True)
    assert slot(monkeypatch, merges, 89 + claim.ROADMAP_IDLE - 1) == (None, claim.ROADMAP, False)   # no quota read


def test_a_refill_with_a_source_does_not_get_the_idle_review(monkeypatch):
    assert slot(monkeypatch, [10], 10 + claim.ROADMAP_IDLE, starved=False) == (None, claim.ROADMAP, True)


def test_no_merged_pr_since_the_last_review_waits(monkeypatch):
    """A review that left no work that a run merged does not come again each idle hour: it waits for a change."""
    assert slot(monkeypatch, [], 10 * claim.ROADMAP_IDLE) == (None, claim.ROADMAP, False)


def test_the_early_gap_stays(monkeypatch):
    merges = [5] * claim.ROADMAP_EARLY
    assert slot(monkeypatch, merges, 6) == (f"{claim.ROADMAP_EARLY}pr-20261031T123358Z-1", claim.ROADMAP_EARLY, True)
