"""Sicilian builders build fortifications and town centers faster (#2115, AoE2 DE wiki): BUILD_OF in
game/data/civs.jsonl. A site is complete after its time divided by the factor of the data. Fake server."""
import pytest

from game import build, civs
from test_treadmill_crane import castle

NAMES = ("CASTLE", "PALISADE_WALL", "STONE_WALL", "TOWN_CENTER", "WATCH_TOWER")


def done_after(civ, name):
    """The site of name of a builder of civ: complete just after its time / factor, not just before."""
    server, g = castle(civ)
    f, t = civs.build_rate(g, name), build.BUILD_TIMES[name]
    a, b = build.found(g, name, (12, 14, 8, 10)), build.found(g, name, (2, 4, 2, 4))
    return f, not build.rise(g, a, t / f - 0.01) and build.rise(g, b, t / f + 0.01)


@pytest.mark.parametrize("name", NAMES)
def test_sicilian_fortifications_and_town_centers_build_in_the_time_of_the_factor(name):
    assert done_after("SICILIANS", name) == (pytest.approx(civs.BUILD_OF["SICILIANS"].get(name, 1.0)), True)


@pytest.mark.parametrize("civ, name", [("SICILIANS", "HOUSE"), ("BRITONS", "CASTLE"), ("BRITONS", "TOWN_CENTER")])
def test_other_buildings_and_civilizations_build_in_their_time(civ, name):
    assert done_after(civ, name) == (pytest.approx(civs.BUILD_OF.get(civ, {}).get(name, 1.0)), True)


def test_the_names_are_buildings():
    assert {n for b in civs.BUILD_OF.values() for n in b} <= set(build.BUILD_TIMES)
