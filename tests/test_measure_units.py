"""The measurement of many moving units (#943, part of #398)."""
import os
import shutil
import sys
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import measure_units as mu  # noqa: E402


def test_unit_uuid_string_and_int_array_agree():
    for i in (0, 5, 70000):
        s, ints = mu.unit_uuid(i)
        assert uuid.UUID(s).int == sum((v % (1 << 32)) << (96 - 32 * k) for k, v in enumerate(ints))
        assert all(-(1 << 31) <= v < 1 << 31 for v in ints)
    assert len({mu.unit_uuid(i)[0] for i in range(1000)}) == 1000


def test_homes_near_the_center_and_deterministic():
    cells = [(x, z) for x in range(10) for z in range(10)]
    h = mu.homes(cells, 4)
    assert len(set(h)) == 4 and all(3 <= x <= 6 and 3 <= z <= 6 for x, z in h)
    assert mu.homes(cells, 150) == mu.homes(cells, 150) and len(mu.homes(cells, 150)) == 150


def test_parse_and_report():
    assert mu.parse("Average time per tick: 7.0ms (Target: 50.0ms)\nPercentiles: P50: 6.1ms P95: 9.0ms P99: 28.0ms") == (7.0, 28.0)
    rows = [{"units": 200, "rate": 2216.4, "mean": 7.0, "p99": 28.0, "moved": 1.0},
            {"units": 1000, "rate": 900, "mean": 80.0, "p99": 120.0, "moved": 0.95}]
    out = mu.report(rows)
    assert "200 | 2216 | 7.00 | 28.00 | 20.0 | 100%" in out and "1000 | 900 | 80.00 | 120.00 | 12.5 | 95%" in out


@pytest.mark.mc
def test_twenty_units_move_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not available")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    rows = mu.measure(str(world), [20], seconds=10, log=None)
    assert rows[0]["units"] == 20 and rows[0]["moved"] == 1.0 and rows[0]["rate"] > 50 and rows[0]["mean"] > 0
