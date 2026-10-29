"""The Fortified Church of the Armenians and Georgians in place of the Monastery (#1930). Georgian villagers in the
square around an own complete church build and repair faster (the key "church_rate" of game/data/civs.jsonl)."""
import pytest
import test_repair
from test_repair_civs import players
from test_train_knight import menu, setup

from game import build, civs, monk, repair, train

NEAR, FAR = (8, 11, 8, 11), (30, 33, 30, 33)                          # block footprints (tile size 1) near and far of v0
_, SQUARE, RATE = civs.value("church_rate", "GEORGIANS")


def church(g, rect):
    g.sites.append({"name": "FORTIFIED_CHURCH", "player": 1, "done": True, "footprint": list(rect)})


def test_the_church_trains_the_monk_holds_relics_and_counts_as_a_monastery_for_the_imperial_age():
    server, g = setup("FORTIFIED_CHURCH")
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = "GEORGIANS"
    rect = train.open_menu(g, "Steve", (11, 3))
    assert ":Monk:" in menu(server) and train.trains(g, "FORTIFIED_CHURCH") == train.trains(g, "MONASTERY")
    assert train.order(g, "Steve", rect, train.ITEMS["MONK"][0]) == 1
    assert monk.monasteries(g) == {rect}
    assert train.missing(g, "IMPERIAL_AGE").endswith("(1/2)")             # the church is one of the two


def repaired(civ, rect=None):
    """The hit points that one villager of player 1 (civ) repairs on a house in two ticks, with a church at rect."""
    server, g = test_repair.setup(house=100)
    players(g, (1, civ, None))
    if rect:
        church(g, rect)
    k = repair.uuid(test_repair.HOUSE)
    repair.order(g, "Steve", (4, 5))
    before = server.hp[k]
    g.villagers["v0"].state = "repair"
    repair.tick(g, 8.0)
    repair.tick(g, 8.0)
    return server.hp[k] - before


def test_a_georgian_villager_near_an_own_church_repairs_faster():
    plain = repaired("GEORGIANS")
    assert repaired("GEORGIANS", NEAR) == pytest.approx(plain * RATE, abs=1)
    assert repaired("GEORGIANS", FAR) == plain
    assert repaired("ARMENIANS", NEAR) == repaired("ARMENIANS")        # a Georgian bonus


def test_georgian_builders_near_an_own_church_work_faster():
    _, g = test_repair.setup()
    players(g, (1, "GEORGIANS", None))
    site = {"name": "HOUSE", "player": 1, "footprint": [4, 6, 4, 6], "progress": 0.0, "commands": [], "sent": 0}
    build.rise(g, site, 10.0)
    plain = site["progress"]
    church(g, NEAR)
    site["progress"] = 0.0
    build.rise(g, site, 10.0)
    assert site["progress"] == pytest.approx(plain * RATE)
    edge = 8 + 1.5 + SQUARE // 2                                       # the east edge of the square around NEAR
    assert civs.church_rate(g, (edge, 9.5)) == RATE and civs.church_rate(g, (edge + 1, 9.5)) == 1
