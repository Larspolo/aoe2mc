"""The pacer maximum reaches the 5-hour limit (owner, 2026-10-27): at the measured burn, the run count carries 90 % of
the window in its first 3 hours, and the cap per cycle (`max_fire`) limits the runs that start. The tests give the caps
of `agent.toml` as arguments: a change of the configuration does not change them."""
import usage

NOW = 1_800_000_000
H = 3600


def test_the_cap_carries_the_window_to_its_aim():
    u = {"five_hour": (0.02, NOW + 4.9 * H, "allowed")}                    # a new window
    n = usage.target_runs(u, NOW, burn=0.009, hi=100)
    assert n == round(0.88 / 2.9 / 0.009) == 34                            # a cap of 16 used about 70 % of a window
    assert usage.target_runs(u, NOW, burn=0.009, hi=16) == 16


def test_the_pacer_starts_up_to_max_fire_runs_per_cycle():
    assert usage.runs_to_start(target=34, claims=16, ready=30, paused=False, hi=8) == 8
    assert usage.lane_plan(34, 16, 30, 0, 0.25, False, hi=8) == (8, 0)
