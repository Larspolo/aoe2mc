"""#2852: the lane weight has a standard error; a noisy fit keeps the start weight of agent.toml."""
import numpy as np
from test_lane_weights import lines

import health


def test_clean_samples_give_the_true_weight_and_a_small_error():
    weights, source, errors, pairs = health.lane_fit(lines([(4, 0), (2, 4), (3, 2), (1, 6), (4, 1)] * 6, weight=0.1))
    assert abs(weights["haiku"] - 0.1) < 0.02 and source["haiku"] == "measured"
    assert errors["haiku"] < 0.05 and pairs == 29


def test_noisy_samples_give_a_large_error_and_the_start_weight():
    rows = [(4, 0), (2, 4), (3, 2), (1, 6), (4, 1)] * 6
    c = lines(rows, weight=0.1)
    out, rng = [], np.random.default_rng(1)
    for line in c[0]["body"].splitlines():                       # shift each usage value by up to 2 points
        head, used, tail = line.split(" · ", 2)
        pct = float(used.split()[1].rstrip("%")) + rng.uniform(-2, 2)
        out.append(f"{head} · usage {max(pct, 0):.1f}% · {tail}")
    weights, source, errors, _ = health.lane_fit([{"body": "\n".join(out)}])
    assert errors["haiku"] > 0.1 and source["haiku"].startswith("noisy, fit ")
    assert weights["haiku"] == 0.25 and health.lane_weights([{"body": "\n".join(out)}])[0]["haiku"] == 0.25
