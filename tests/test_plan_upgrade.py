"""After a plan upgrade the pacer uses the larger quota within hours, not after a day (#1706)."""
import datetime

import health
import usage
from agent_config import CONFIG

T0 = datetime.datetime(2026, 10, 27, 0, tzinfo=datetime.timezone.utc)
RESET = T0 + datetime.timedelta(days=2)       # one fake window: burn_ratio only needs the same reset time
Q = 0.25                                      # hours between two samples


def samples(rates, claims=1):
    """5-hour samples every Q hours: each rate is the burn of one run-hour in that interval."""
    out, used = [(T0, 0.0, RESET, claims)], 0.0
    for i, r in enumerate(rates, 1):
        used += r * Q * claims
        out.append((T0 + datetime.timedelta(hours=i * Q), used, RESET, claims))
    return out


def test_the_burn_follows_a_drop_of_the_last_two_hours():
    s = samples([0.040] * 88 + [0.010] * 8)                                  # 22 h at 0.040, then 2 h at 0.010
    assert abs(health.burn_ratio(s) - 0.010) < 1e-9
    assert abs(health.burn_ratio(samples([0.040] * 96)) - 0.040) < 1e-9      # no drop: the whole period


def test_a_short_or_small_dip_keeps_the_whole_period():
    assert health.burn_ratio(samples([0.040] * 92 + [0.010] * 4)) > 0.035   # 1 h: fewer than 5 intervals
    assert health.burn_ratio(samples([0.040] * 88 + [0.030] * 8)) > 0.035   # 0.030 is more than half of 0.039


def test_the_weekly_burn_follows_a_drop_too():
    def line(h, w):
        return (f"Usage: {T0 + datetime.timedelta(hours=h):%Y-%m-%dT%H:%M:%SZ} · usage 10.0% · resets "
                f"2026-10-27T17:30:00Z · runs 1 · week {w:.4f}%")
    w, rows = 40.0, []
    for i in range(97):
        rows.append(line(i * Q, w))
        w += (0.0052 if i < 88 else 0.0013) * Q * 100
    now = T0 + datetime.timedelta(hours=24)
    assert abs(health.weekly_burn([{"body": "\n".join(rows)}], now) - 0.0013) < 1e-6


def test_the_cap_comes_from_agent_toml():
    assert usage.HI == CONFIG.get("pacing", {}).get("max_runs", 16)
    u = {"five_hour": (0.10, 4.2 * 3600, "allowed")}
    assert usage.target_runs(u, 0, burn=0.010, hi=40) == round(0.8 / 2.2 / 0.010) == 36   # a 4 times larger quota
    n = max(usage.LO, min(usage.HI, 36))
    assert usage.target_runs(u, 0, burn=0.010) == n
    assert f"max {usage.HI} runs · target {n} runs" in usage.describe(u, 0, 0.010)
