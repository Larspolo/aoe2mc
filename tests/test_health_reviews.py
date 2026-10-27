"""The review slots in tools/health.py: each slot of the process review gets its review in time (#942)."""
import datetime

import health

T = 1793000000                                  # a unix time


def test_review_delays_from_the_claim_refs():
    lines = [f"review-180m-166022 {T + 180 * 60 + 600} Claim review 180m-166022 by b",
             f"review-90m-332042 {T} Claim review 90m-332042 by a",
             f"1704 {T + 60} Claim 1704 by c",                               # a ticket claim: not a review
             f"review-360m-83012 {T + (180 + 360) * 60 + 1800 + 600} Claim review 360m-83012 by d"]
    d = health.review_delays(lines)
    assert [(m, late) for _, m, late in d] == [(90, None), (180, 10), (360, 30)]
    assert d[0][0] == datetime.datetime.fromtimestamp(T, datetime.timezone.utc)


def test_the_report_has_the_review_slots():
    since = datetime.datetime.fromtimestamp(T - 3600, datetime.timezone.utc)
    reviews = health.review_delays([f"review-90m-1 {T} s", f"review-180m-2 {T + 200 * 60} s"])
    text = health.report(since, [], [], [], [], [], [], reviews=reviews)
    line = next(x for x in text.splitlines() if x.startswith("Review slots"))
    assert line.endswith(f"{reviews[0][0]:%m-%d %H:%M} 90 -; {reviews[1][0]:%m-%d %H:%M} 180 +20")
    assert "Review slots" not in health.report(since, [], [], [], [], [], [])
