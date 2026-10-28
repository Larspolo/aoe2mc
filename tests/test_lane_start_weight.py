"""#3137: a lane with too few intervals for a fit counts its start weight in the fit of the other lanes."""
import datetime

import health
import usage

T0 = datetime.datetime(2026, 10, 28, 0, tzinfo=datetime.timezone.utc)
RESET = T0 + datetime.timedelta(days=2)


def lines(rows, step=0.25, burn=0.04, weights=None):
    """`Usage:` lines every `step` hours. rows: (Opus, Haiku, deep runs) at each sample; a lane run uses its weight of
    the quota of an Opus run, and the runs of an interval are the mean of its two samples."""
    w = weights or {"haiku": 0.1, "deep": 4.0}
    used, out, eq = 0.10, [], [o + w["haiku"] * h + w["deep"] * d for o, h, d in rows]
    for i, (o, h, d) in enumerate(rows):
        t = T0 + datetime.timedelta(hours=i * step)
        out.append(usage.sample_line({"five_hour": (used, RESET.timestamp(), "allowed")}, t.timestamp(), o + h + d,
                                     lanes={"opus": o, "haiku": h, "deep": d}))
        used += burn * step * (eq[i] + eq[min(i + 1, len(eq) - 1)]) / 2
    return [{"body": "\n".join(out)}]


def test_a_few_deep_runs_do_not_move_the_haiku_weight():
    rows = [(4, 0, 0), (2, 4, 0), (3, 2, 0), (1, 6, 0), (4, 1, 0)] * 6
    rows[10:13] = [(1, 2, 3)] * 3                                  # 4 intervals with deep runs: fewer than `need`
    weights, source, errors, _ = health.lane_fit(lines(rows))
    assert source["deep"] == "start" and weights["deep"] == health.LANES["deep"]
    assert abs(weights["haiku"] - 0.1) < 0.02 and source["haiku"] == "measured"


def test_with_no_deep_runs_the_haiku_weight_stays_the_same():
    rows = [(4, 0, 0), (2, 4, 0), (3, 2, 0), (1, 6, 0), (4, 1, 0)] * 6
    weights, source, _, _ = health.lane_fit(lines(rows))
    assert abs(weights["haiku"] - 0.1) < 0.02 and source["haiku"] == "measured"
