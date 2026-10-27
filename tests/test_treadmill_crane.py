"""Treadmill Crane at the university (#1422): Castle Age, 200 wood and 50 stone, 20 s (AoE2 DE wiki infobox
"Treadmill Crane"); after it, the builders of the player work 20 % faster. Fake server."""
from test_build_site import site_map

from game import build, civs, train


def castle(civ="TEUTONS", techs=()):
    server, g = site_map()
    g.data["players"]["1"]["civ"] = civ
    g.techs |= set(build.AGE_TECHS[:2]) | set(techs)
    return server, g


def test_the_university_has_treadmill_crane_in_the_castle_age():
    assert (train.COSTS["TREADMILL_CRANE"], train.TRAIN_TIMES["TREADMILL_CRANE"], train.TECH_AGE["TREADMILL_CRANE"]) \
        == ({"wood": 200, "stone": 50}, 20, 2)
    assert "TREADMILL_CRANE" in train.TRAINS["UNIVERSITY"] and train.HELP["TREADMILL_CRANE"]
    server, g = castle()
    assert train.unlocked(g, "TREADMILL_CRANE")
    g.techs.discard("CASTLE_AGE")
    assert not train.unlocked(g, "TREADMILL_CRANE")
    server, g = castle("PERSIANS")                                    # the wiki availability chart
    assert "PERSIANS" in civs.MISSING["TREADMILL_CRANE"] and not train.unlocked(g, "TREADMILL_CRANE")


def test_a_site_is_complete_in_1_of_1_2_of_the_time_after_the_research():
    t = build.BUILD_TIMES["HOUSE"]
    server, g = castle()
    g.stock.update(wood=50)
    site = build.found(g, "HOUSE", (12, 14, 8, 10))
    assert not build.rise(g, site, t / 1.2 + 0.01)                     # no Treadmill Crane: 25 s
    g.techs.add("TREADMILL_CRANE")
    other = build.found(g, "HOUSE", (2, 4, 2, 4))
    assert not build.rise(g, other, t / 1.2 - 0.01) and build.rise(g, other, 0.02)
