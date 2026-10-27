"""The build speed bonuses of the civilizations (#1893, AoE2 DE wiki): Spanish builders work 30 % faster (20 % for
wonders), Roman builders 5 % faster; Treadmill Crane multiplies with them. Fake server."""
import pytest

from game import build, civs
from test_treadmill_crane import castle

T = build.BUILD_TIMES["HOUSE"]                                         # 25 s


def done_after(civ, techs=()):
    """The site of a house of a builder of civ: complete just after T / factor, not just before."""
    server, g = castle(civ, techs)
    g.stock.update(wood=100)
    f = civs.build_rate(g, "HOUSE") * build.CRANE ** bool(techs)
    a, b = build.found(g, "HOUSE", (12, 14, 8, 10)), build.found(g, "HOUSE", (2, 4, 2, 4))
    return f, not build.rise(g, a, T / f - 0.01) and build.rise(g, b, T / f + 0.01)


@pytest.mark.parametrize("civ, factor", [("SPANISH", 1.3), ("ROMANS", 1.05), ("BRITONS", 1.0)])
def test_builders_of_a_civilization_work_at_its_rate(civ, factor):
    assert done_after(civ) == (pytest.approx(factor), True)


def test_spanish_wonder_sites_get_20_percent():
    server, g = castle("SPANISH")
    assert civs.build_rate(g, "WONDER") == 1.2 and civs.build_rate(g, "HOUSE") == 1.3
    server, g = castle("ROMANS")
    assert civs.build_rate(g, "WONDER") == 1.05


def test_treadmill_crane_multiplies_with_the_bonus():
    assert done_after("SPANISH", ("TREADMILL_CRANE",)) == (pytest.approx(1.3 * 1.2), True)
