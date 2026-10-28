"""The dropped review locks in tools/health.py: a lock that a later lock of its slot followed did not finish (#3337)."""
import datetime

import health

T = 1793000000                                  # a unix time: 2026-10-26 07:33:20 UTC
at = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc)
key = lambda t: f"{at(t):%Y%m%dT%H%M%SZ}"       # the `<last review>` of a lock key
merged = [at(T + 60 * m) for m in range(1, 120)]                       # one PR each minute


def test_a_lock_that_a_later_lock_of_its_slot_followed_is_dropped():
    lines = [f"review-50pr-{key(T)}-1 {T + 1000} Claim review by a",    # not finished: the slot opened again
             f"review-50pr-{key(T)}-2 {T + 2000} Claim review by b"]
    d = health.review_delays(lines, merged, at(T))
    assert [(g, late) for _, g, late in d] == [(50, health.DROPPED), (50, -67)]   # 33 PRs - 2 gaps
    assert [x for *_, x in health.review_delays(lines, merged, at(T + 1500))] == [health.DROPPED, None]


def test_a_later_lock_with_another_review_time_is_not_dropped():
    lines = [f"review-50pr-{key(T)}-1 {T + 1000} Claim review by a",
             f"review-50pr-{key(T + 1600)}-1 {T + 3000} Claim review by b"]
    d = health.review_delays(lines, merged, at(T))
    assert [x for *_, x in d] == [-34, -26]                 # counted from each own last review, not the lock before
    since = at(T - 3600)
    reviews = health.review_delays(lines, merged, since)
    text = health.report(since, [], [], [], [], [], [], reviews=reviews)
    line = next(x for x in text.splitlines() if x.startswith("Review slots"))
    assert line == (f"Review slots (taken UTC, gap PRs, PRs late): {at(T + 1000):%m-%d %H:%M} 50 -34; "
                    f"{at(T + 3000):%m-%d %H:%M} 50 -26")


def test_the_report_names_a_dropped_slot():
    since = at(T - 3600)
    lines = [f"review-50pr-{key(T)}-1 {T + 1000} Claim review by a",
             f"review-50pr-{key(T)}-2 {T + 2000} Claim review by b"]
    text = health.report(since, [], [], [], [], [], [], reviews=health.review_delays(lines, merged, since))
    line = next(x for x in text.splitlines() if x.startswith("Review slots"))
    assert line == (f"Review slots (taken UTC, gap PRs, PRs late): {at(T + 1000):%m-%d %H:%M} 50 dropped; "
                    f"{at(T + 2000):%m-%d %H:%M} 50 -67")
