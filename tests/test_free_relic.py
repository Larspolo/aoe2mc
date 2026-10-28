"""The first Fortified Church of an Armenian player gets a free relic (#2419, AoE2 DE wiki "Armenians": "the first one
constructed receives a free Relic"; "Fortified Church": "The first Armenian Fortified Church provides a free garrisoned
Relic"). Key free_relic of game/data/civs.jsonl. Fake server."""
from game import build, monk
from test_treadmill_crane import castle


def church(g, rect):
    site = build.found(g, "FORTIFIED_CHURCH", rect)
    assert build.rise(g, site, build.BUILD_TIMES["FORTIFIED_CHURCH"])
    return tuple(site["footprint"])


def test_the_first_armenian_church_holds_a_relic_that_gives_gold():
    _, g = castle("ARMENIANS")
    home = church(g, (12, 15, 8, 11))
    assert [r for r in monk.relics(g) if r["home"]] == [{"at": None, "monk": None, "home": home, "free": True,
                                                          "player": 1}]
    gold = g.stock["gold"]
    for _ in range(60):
        monk.relic_tick(g, monk.EVERY)
    assert g.stock["gold"] - gold == 30                                 # 30 gold per AoE2 minute of one relic


def test_the_second_church_holds_none():
    _, g = castle("ARMENIANS")
    church(g, (12, 15, 8, 11))
    church(g, (2, 5, 12, 15))
    assert sum(r["home"] is not None for r in monk.relics(g)) == 1


def test_a_georgian_church_and_an_armenian_monastery_hold_none():
    for civ, name in (("GEORGIANS", "FORTIFIED_CHURCH"), ("ARMENIANS", "MONASTERY")):
        _, g = castle(civ)
        site = build.found(g, name, (12, 15, 8, 11))
        assert build.rise(g, site, build.BUILD_TIMES[name])
        assert not any(r["home"] for r in monk.relics(g))
