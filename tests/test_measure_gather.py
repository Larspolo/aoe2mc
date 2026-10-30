"""tools/measure_gather.py per resource (#393): the AoE2 values, the table, and one real server run per resource."""
import measure_gather
import pytest


def test_aoe2_values_and_table_per_resource():
    m = {"walk": 4.0, "chop": 1.0, "trip": 26.0, "trip_blocks": 62}
    conf = measure_gather.configured(0.25, 1.0, 10, 62)
    for res, label in (("wood", "Chop (wood/s)"), ("food", "Forage (food/s)"), ("farm", "Farm (food/s)"),
                       ("gold", "Mine (gold/s)"), ("stone", "Mine (stone/s)")):
        work = measure_gather.AOE2_WORK[res]
        assert f"| {label} | 1.00 | 1.00 | {work:.2f} | {work * 1.7:.2f} |" in measure_gather.table(m, conf, 4, res)
        a = measure_gather.aoe2(4, 62, 1.0, res)
        assert a["trip"] == pytest.approx(62 / 3.2 + 10 / work)


@pytest.mark.mc
@pytest.mark.parametrize("resource", ["food", "farm", "gold", "stone"])
def test_measured_rates_per_resource(resource):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    events, T = measure_gather.measure(distance=10, loads=2, resource=resource)
    m = measure_gather.analyze(events)
    conf = measure_gather.configured(0.25, measure_gather.WORK_SECONDS[resource], 10, m["trip_blocks"],
                                     measure_gather.ai.walk_speed("VILLAGER", T))       # Paper (#437)
    print(measure_gather.table(m, conf, T, resource))
    for k in ("walk", "chop", "trip"):
        assert m[k] == pytest.approx(conf[k], rel=0.1), (k, m[k], conf[k])
