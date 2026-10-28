"""The Fortified Church of the Armenians and Georgians in place of the Monastery (#1930, AoE2 DE wiki "Fortified
Church": 200 wood, 50 s, Castle Age, 2400 hit points, armor 4/10, line of sight 10). Georgian villagers in the 21-tile
square around an own complete church build and repair 10 % faster (AoE2 wiki "Georgians", "Repairing")."""
import pytest
import test_repair
from test_build_menu import villager_map
from test_krepost import shown
from test_repair_civs import players
from test_train_knight import menu, setup

from game import build, civs, combat, monk, repair, train

NEAR, FAR = (8, 11, 8, 11), (30, 33, 30, 33)                          # block footprints (tile size 1) near and far of v0


def church(g, rect):
    g.sites.append({"name": "FORTIFIED_CHURCH", "player": 1, "done": True, "footprint": list(rect)})


def test_a_georgian_player_has_the_church_and_no_monastery_in_the_build_menu():
    server, g = villager_map()                                         # Britons
    build.open_menu(g, "Steve")
    assert "Monastery" in shown(server) and "Fortified Church" not in shown(server)
    for civ in ("GEORGIANS", "ARMENIANS"):
        g.data["players"]["1"]["civ"] = civ
        build.open_menu(g, "Steve")
        assert "Fortified Church" in shown(server) and "Monastery" not in shown(server), civ
    item = next(it for it in build.items(g) if it[2] == "Fortified Church")
    assert item[0] == build.MENU.index("FORTIFIED_CHURCH") and item[3] == "200 wood\n50 s\nNeeds the Castle Age"
    server.chosen = build.MENU.index("MONASTERY") + 1                  # also not with /trigger
    assert build.chosen(g, "Steve") is None


def test_the_values_of_the_wiki():
    s = combat.BUILDINGS["FORTIFIED_CHURCH"]
    assert (s.hp, s.attack, s.melee, s.pierce, s.range) == (2400, 5, 4, 10, 4) and combat.SIGHT["FORTIFIED_CHURCH"] == 10
    assert build.BUILD_TIMES["FORTIFIED_CHURCH"] == 50
    assert set(civs.MISSING["MONASTERY"]) == {"ARMENIANS", "GEORGIANS"}
    assert set().union(*civs.MISSING.values()) - set(civs.MISSING["FORTIFIED_CHURCH"]) == {"ARMENIANS", "GEORGIANS"}


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


def test_a_georgian_villager_near_an_own_church_repairs_10_percent_faster():
    plain = repaired("GEORGIANS")
    assert repaired("GEORGIANS", NEAR) == pytest.approx(plain * 1.1, abs=1)
    assert repaired("GEORGIANS", FAR) == plain
    assert repaired("ARMENIANS", NEAR) == repaired("ARMENIANS")        # a Georgian bonus


def test_georgian_builders_near_an_own_church_work_10_percent_faster():
    _, g = test_repair.setup()
    players(g, (1, "GEORGIANS", None))
    site = {"name": "HOUSE", "player": 1, "footprint": [4, 6, 4, 6], "progress": 0.0, "commands": [], "sent": 0}
    build.rise(g, site, 10.0)
    plain = site["progress"]
    church(g, NEAR)
    site["progress"] = 0.0
    build.rise(g, site, 10.0)
    assert site["progress"] == pytest.approx(plain * 1.1)
    assert civs.church_rate(g, (19.5, 9.5)) == 1.1 and civs.church_rate(g, (20.5, 9.5)) == 1
