"""The measured burn is a ratio of sums, so that intervals with few claims do not raise it (#582)."""
import datetime

import health
import usage

NOW = datetime.datetime(2026, 10, 26, 6, 0, tzinfo=datetime.timezone.utc)
RESET = NOW + datetime.timedelta(hours=1)


def line(h, used, claims, reset=RESET):
    t = (NOW - datetime.timedelta(hours=h)).timestamp()
    return {"body": usage.sample_line({"five_hour": (used, reset.timestamp(), "allowed")}, t, claims)}


def test_few_claims_do_not_raise_the_burn():
    # 0.30 in 1 h by 10 runs, then 0.10 in 1 h while only 1 run holds a claim (the others are between tickets)
    s = health.samples([line(2, 0.30, 10), line(1, 0.60, 10), line(0.5, 0.65, 1), line(0, 0.70, 1)])
    assert abs(health.burn_ratio(s, need=1) - 0.40 / (10 + 0.5 * 5.5 + 0.5 * 1)) < 1e-9    # 0.030
    assert max(health.burn_pairs(s)) > 0.05                                                # one pair gives 0.1


def test_a_reset_is_not_a_rise_and_duplicates_count_once():
    other = NOW - datetime.timedelta(hours=4)
    s = health.samples([line(3, 0.9, 10, other), line(2, 0.1, 10), line(2, 0.1, 10), line(1, 0.4, 10)])
    assert abs(health.burn_ratio(s, need=1) - 0.03) < 1e-9


def test_no_burn_without_enough_intervals_or_claims():
    assert health.burn_ratio(health.samples([line(2, 0.3, 10), line(1, 0.6, 10)]), need=2) is None
    assert health.burn_ratio(health.samples([line(2, 0.3, 0), line(1, 0.4, 0)]), need=1) is None
