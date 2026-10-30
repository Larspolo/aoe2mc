"""The build speed bonuses of the civilizations (#1893, AoE2 DE wiki: Spanish and Roman builders work faster, civs.
build_rate); Treadmill Crane multiplies with them. Fake server."""
import pytest
from test_treadmill_crane import castle

from game import build, civs

T = build.BUILD_TIMES["HOUSE"]


def done_after(civ, techs=()):
    """The site of a house of a builder of civ: complete just after T / factor, not just before."""
    server, g = castle(civ, techs)
    g.stock.update(wood=100)
    f = civs.build_rate(g, "HOUSE") * build.CRANE ** bool(techs)
    a, b = build.found(g, "HOUSE", (12, 14, 8, 10)), build.found(g, "HOUSE", (2, 4, 2, 4))
    return f, not build.rise(g, a, T / f - 0.01) and build.rise(g, b, T / f + 0.01)


@pytest.mark.parametrize("civ", ["BRITONS", "ROMANS", "SPANISH"])
def test_builders_of_a_civilization_work_at_its_rate(civ):
    assert done_after(civ)[1]


def test_treadmill_crane_multiplies_with_the_bonus():
    f, done = done_after("SPANISH", ("TREADMILL_CRANE",))
    assert done and f == pytest.approx(done_after("SPANISH")[0] * build.CRANE)
