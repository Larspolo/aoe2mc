"""framework/tools/health.py measures the burn of one run from the `Usage:` lines, and framework/tools/usage.py uses it (#462)."""
import datetime

import health
import usage

NOW = datetime.datetime(2026, 10, 26, 6, 0, tzinfo=datetime.timezone.utc)
RESET = NOW + datetime.timedelta(hours=1)


def line(h, used, claims, reset=RESET):
    t = (NOW - datetime.timedelta(hours=h)).timestamp()
    return usage.sample_line({"five_hour": (used, reset.timestamp(), "allowed")}, t, claims)


def test_sample_line_round_trips():
    s = health.samples([{"body": "Run of x.\n" + line(2, 0.305, 9) + "\nMetrics: ..."}])
    assert s == [(NOW - datetime.timedelta(hours=2), 0.305, RESET, 9)]


def test_burn_pairs_divide_by_hours_and_claims():
    c = [{"body": line(2, 0.30, 10)}, {"body": line(1, 0.60, 10)}]
    assert health.burn_pairs(health.samples(c)) == [0.03]
    two = [{"body": line(2, 0.30, 8)}, {"body": line(1.5, 0.45, 12)}]          # 0.15 in 0.5 h by 10 runs
    assert abs(health.burn_pairs(health.samples(two))[0] - 0.03) < 1e-9


def test_burn_pairs_skip_a_reset_a_short_gap_and_no_runs():
    other = NOW - datetime.timedelta(hours=4)
    assert health.burn_pairs(health.samples([{"body": line(2, 0.9, 10, other)}, {"body": line(1, 0.1, 10)}])) == []
    assert health.burn_pairs(health.samples([{"body": line(1.1, 0.3, 10)}, {"body": line(1, 0.4, 10)}])) == []
    assert health.burn_pairs(health.samples([{"body": line(2, 0.3, 0)}, {"body": line(1, 0.3, 0)}])) == []


def test_measured_burn_needs_five_pairs_of_the_last_day():
    c = [{"body": line(h, 0.9 - 0.04 * h, 10)} for h in (5, 4, 3, 2, 1)]       # 4 pairs, 0.004 each
    assert health.measured_burn(c, NOW) is None
    c.append({"body": line(0, 0.9, 10)})
    assert abs(health.measured_burn(c, NOW) - 0.004) < 1e-9
    assert health.measured_burn(c, NOW + datetime.timedelta(hours=22)) is None   # old samples do not count


def test_target_uses_the_burn():
    u = {"five_hour": (0.3, NOW.timestamp() + 2 * 3600, "allowed")}
    assert usage.target_runs(u, NOW.timestamp(), burn=0.05) == round((usage.END - 0.3) / 2 / 0.05)   # the last 2 hours
    assert "burn 0.050" in usage.describe(u, NOW.timestamp(), 0.05)
