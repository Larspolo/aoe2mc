"""The pacer maximum reaches the 5-hour limit (owner, 2026-10-27): at the measured burn, `max_runs` carries 90 % of
the window in its first 3 hours, and `max_fire` starts the runs fast enough to get there."""
import usage

NOW = 1_800_000_000
H = 3600


def test_the_cap_carries_the_window_to_its_aim():
    u = {"five_hour": (0.02, NOW + 4.9 * H, "allowed")}                    # a new window
    n = usage.target_runs(u, NOW, burn=0.009)
    assert n == round(0.88 / 2.9 / 0.009) == 34 < usage.HI                 # 16 was the cap: about 70 % of a window


def test_the_pacer_starts_up_to_max_fire_runs_per_cycle():
    assert usage.MAX_FIRE == 8
    assert usage.runs_to_start(target=34, claims=16, ready=30, paused=False) == 8
    assert usage.lane_plan(34, 16, 30, 0, 0.25, False) == (8, 0)
