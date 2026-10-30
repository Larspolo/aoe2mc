"""framework/tools/usage.py: below `week_free` of the 7-day usage the runs fill each 5-hour window, above it the weekly guard
counts again (owner, 2026-10-27)."""
import usage

NOW = 1_800_000_000
H = 3600


def five(used=0.3):
    return {"five_hour": (used, NOW + 2 * H, "allowed")}


def test_a_week_below_the_threshold_fills_the_window():
    u = five() | {"seven_day": (0.52, NOW + 145 * H, "allowed")}         # far ahead of the time, but below 60 %
    assert usage.target_runs(u, NOW, burn7=0.0053, free7=0.6, hi=99) == usage.target_runs(five(), NOW, hi=99) == 11
    assert usage.target_runs(u, NOW, free7=0.6, hi=99) == 11              # also without a measured burn7


def test_a_week_above_the_threshold_keeps_the_guard():
    u = five() | {"seven_day": (0.65, NOW + 100 * H, "allowed")}
    assert usage.target_runs(u, NOW, burn7=0.0053, free7=0.6, week=True) == 0   # 0.35 / 100 h / 0.0053 < 1 run
    assert usage.target_runs(five() | {"seven_day": (0.3, NOW + H, "rejected")}, NOW, free7=0.6, week=True) == 0

