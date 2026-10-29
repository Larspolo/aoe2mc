"""Treadmill Crane at the university (#1422): Castle Age (AoE2 DE wiki infobox "Treadmill Crane"); after it,
the builders of the player work faster. Fake server."""
from test_build_site import site_map

from game import build, civs, train


def castle(civ="TEUTONS", techs=()):
    server, g = site_map()
    g.data["players"]["1"]["civ"] = civ
    g.techs |= set(build.AGE_TECHS[:2]) | set(techs)
    return server, g


def test_the_university_has_treadmill_crane_in_the_castle_age():
    server, g = castle()
    assert train.unlocked(g, "TREADMILL_CRANE")
    g.techs.discard("CASTLE_AGE")
    assert not train.unlocked(g, "TREADMILL_CRANE")
    server, g = castle(min(civs.MISSING["TREADMILL_CRANE"]))         # a civilization without it
    assert not train.unlocked(g, "TREADMILL_CRANE")


def test_a_site_is_complete_in_less_time_after_the_research():
    t = build.BUILD_TIMES["HOUSE"]
    server, g = castle()
    g.stock.update(wood=10000)
    site = build.found(g, "HOUSE", (12, 14, 8, 10))
    assert not build.rise(g, site, t - 0.01)                           # no Treadmill Crane: the full time
    g.techs.add("TREADMILL_CRANE")
    other = build.found(g, "HOUSE", (2, 4, 2, 4))
    assert build.rise(g, other, t - 0.01)
