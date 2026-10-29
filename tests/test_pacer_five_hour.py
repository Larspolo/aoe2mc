"""tools/usage.py: `week_guard` of `agent.toml` turns the weekly guard on and off (owner, 2026-10-28)."""
import usage

NOW = 1_800_000_000
H = 3600
AHEAD = {"five_hour": (0.3, NOW + 2 * H, "allowed"), "seven_day": (0.65, NOW + 100 * H, "allowed")}   # above week_free


def test_off_counts_the_five_hour_window_only():
    assert usage.target_runs(AHEAD, NOW, burn7=0.0053, week=False, hi=40, free7=0.6) == 11
    assert usage.target_runs(AHEAD | {"seven_day": (1.0, NOW + 3 * 86400, "rejected")}, NOW, week=False, hi=40) == 11
    assert usage.target_runs({"five_hour": (0.3, NOW + 2 * H, "rejected")}, NOW, week=False) == 0


def test_on_keeps_the_weekly_guard():
    assert usage.target_runs(AHEAD, NOW, burn7=0.0053, week=True, hi=40, free7=0.6) == 0   # 0.35 / 100 h / 0.0053 < 1 run
