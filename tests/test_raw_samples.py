"""health.raw_samples with two equal samples of other lane counts (#4434): no TypeError of the dict compare."""
import health


def test_two_equal_samples_with_other_lanes_sort():
    line = "Usage: 2026-10-30T00:00:00Z · usage 50.0% · resets 2026-10-30T02:00:00Z · runs 3"
    lane = next(iter(health.LANES))
    comments = [{"body": f"{line} · {lane} 1"}, {"body": f"{line} · {lane} 2"}]
    assert [s[4] for s in health.raw_samples(comments)] == [{lane: 1}, {lane: 2}]
