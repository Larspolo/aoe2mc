"""tools/tick_cost.py (#458): the answer of /tick query, the report, and one real server run on the village."""
import pytest
import tick_cost

ANSWER = ("The game is running normallyTarget tick rate: 20.0 per second.\nAverage time per tick: 2.3ms (Target: 50.0ms)"
          "Percentiles: P50: 2.2ms P95: 3.4ms P99: 4.7ms. Sample: 100")


def test_parse_and_report():
    assert tick_cost.parse(ANSWER) == (2.3, 4.7)
    with pytest.raises(ValueError):
        tick_cost.parse("Unknown command")
    text = tick_cost.report({"lines": 14, "with": (1.15, 9.0), "without": (1.0, 7.7)})
    assert "14 lines" in text and "+0.15 ms per tick (limit 2.0 ms)" in text


@pytest.mark.mc
def test_village_pack_costs_less_than_the_limit(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    r = tick_cost.measure(tick_cost.convert("village", str(tmp_path)), seconds=20)
    print(tick_cost.report(r))
    assert r["lines"] > 0
    assert r["with"][0] - r["without"][0] < tick_cost.LIMIT
