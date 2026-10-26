"""The target uses 90 % of the 5-hour window in its first 3 hours, then slows down to 98 % (owner, 2026-10-26, #587)."""
import usage

NOW = 1_800_000_000
H = 3600


def target(used, left_hours, burn=0.05):
    return usage.target_runs({"five_hour": (used, NOW + left_hours * H, "allowed")}, NOW, burn)


def test_fast_to_90_percent_two_hours_before_the_reset():
    assert target(0.06, 4.4) == round((0.90 - 0.06) / 2.4 / 0.05)       # 7 runs
    assert target(0.06, 4.4) > round((0.98 - 0.06) / 4.4 / 0.05)        # more than the even pace (4)


def test_slow_to_98_percent_in_the_last_two_hours():
    assert target(0.90, 2.0) == usage.LO                                # 0.08 in 2 h: less than one run
    assert target(0.80, 1.0) == round((0.98 - 0.80) / 1.0 / 0.05)       # behind the plan: 4 runs


def test_above_90_percent_early_uses_the_end_aim():
    assert target(0.92, 3.0) == usage.LO                                # no negative aim
    assert target(0.50, 2.1) == usage.HI                                # 6 minutes to reach 90 %: as fast as possible
