"""framework/tools/health.py pairs each `Usage:` sample with the first sample 15 minutes later in the same window (#571)."""
import datetime

import health
from test_burn import NOW, line


def test_close_samples_give_pairs():
    # samples 5 minutes apart: 0.30 at 2 h ago, then +0.01 each 5 minutes with 4 runs (0.03 per run hour)
    c = [{"body": line(2 - k / 12, 0.30 + 0.01 * k, 4)} for k in range(7)]
    pairs = health.burn_pairs(health.samples(c))
    assert len(pairs) == 4                                             # sample k pairs with sample k + 3
    assert all(abs(p - 0.03) < 1e-9 for p in pairs)


def test_a_reset_between_two_samples_gives_no_pair():
    other = NOW + datetime.timedelta(hours=5)
    c = [{"body": line(2, 0.80, 4)}, {"body": line(1.9, 0.82, 4)}, {"body": line(1.5, 0.05, 4, other)},
         {"body": line(1.4, 0.06, 4, other)}]
    assert health.burn_pairs(health.samples(c)) == []
    c.append({"body": line(1.2, 0.08, 4, other)})                     # 0.3 h after the first sample of the new window
    assert len(health.burn_pairs(health.samples(c))) == 1
