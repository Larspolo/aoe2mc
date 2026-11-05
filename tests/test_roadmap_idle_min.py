"""The idle roadmap review needs ROADMAP_IDLE_MIN merged PRs (#5818): after 1 or 2 merged PRs (one of them the PR of the
last review) a review finds no change, and the pacer started a deep run for it each idle hour (5 reviews in 8 hours,
2026-11-04)."""
import claim
from test_roadmap_idle import slot


def test_fewer_merged_prs_than_the_minimum_wait_also_after_a_day(monkeypatch):
    merges = [10] * (claim.ROADMAP_IDLE_MIN - 1)
    assert slot(monkeypatch, merges, 24 * 60) == (None, claim.ROADMAP, False)       # no quota read


def test_the_minimum_makes_the_idle_review_due_at_the_merged_count(monkeypatch):
    n = claim.ROADMAP_IDLE_MIN
    assert slot(monkeypatch, [10] * n, 10 + claim.ROADMAP_IDLE) == (f"{n}pr-20261031T123358Z-1", n, True)
