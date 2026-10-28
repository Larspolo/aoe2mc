"""The lane weight is the ratio of the median cost of a lane run to that of an Opus run when each has 10 runs with a
`cost` (#3457), else the fit of the Usage: lines."""
import health


def run(cost, lane=None):
    return {"body": f"Metrics: ticket #5 · size:S · pr #9 · 10 min{f' · lane {lane}' * bool(lane)}\n"
                    f"Tokens: 1.2M eq · cost ${cost:.2f} · peak 1k"}


def test_ten_runs_per_lane_give_the_cost_ratio():
    comments = [run(1.0 + i / 100) for i in range(11)] + [run(0.1, "haiku") for _ in range(10)] + \
        [run(3.15, "deep") for _ in range(10)]
    weights, source = health.lane_weights(comments)
    assert round(weights["haiku"], 3) == 0.095 and round(weights["deep"], 2) == 3.0
    assert source["haiku"] == source["deep"] == "cost"


def test_fewer_runs_keep_the_old_weight():
    comments = [run(1.0) for _ in range(10)] + [run(0.1, "haiku") for _ in range(9)]
    weights, source = health.lane_weights(comments)
    assert source["haiku"] != "cost" and weights["haiku"] == health.lane_weights([])[0]["haiku"]
