"""game/train.py: the university researches Architecture (300 food, 200 wood, 70 s, after Masonry) and Arrowslits
(250 food, 250 wood, 25 s) in the Imperial Age (AoE2 DE wiki), #1504. Architecture: the buildings +10 % hit points and
+1/+1 armor, as Masonry. Arrowslits: a watch tower +1, a guard tower +2 and a keep +3 attack."""
from test_loom import menus
from test_tower_upgrades import MAP, research, setup, uuid

from game import build, civs, combat, train

TC = (2, 5, 2, 5)


def test_the_cost_time_age_and_order_are_those_of_aoe2():
    assert train.AFTER["ARCHITECTURE"] == "MASONRY"
    assert {"ARCHITECTURE", "ARROWSLITS"} <= set(train.TRAINS["UNIVERSITY"])


def test_the_university_menu_shows_both_in_the_imperial_age_and_architecture_after_masonry():
    for age, shown in ((2, False), (3, True)):
        server, g = setup(age)
        train.open_menu(g, "Steve", (9, 9))
        assert (":book:Arrowslits:" in menus(server)[-1]) == shown
        assert ":book:Architecture:" not in menus(server)[-1]          # Masonry first
    assert "19:book:Arrowslits:250 food · 250 wood · 25 s · research" in menus(server)[-1]
    g.techs.add("MASONRY")
    train.open_menu(g, "Steve", (9, 9))
    assert "6:book:Architecture:300 food · 200 wood · 70 s · research" in menus(server)[-1]


def test_a_civilization_without_the_technology_does_not_see_it():
    assert "MONGOLS" in civs.MISSING["ARCHITECTURE"] and "BRITONS" not in civs.MISSING["ARCHITECTURE"]
    assert "GOTHS" in civs.MISSING["ARROWSLITS"] and "TEUTONS" not in civs.MISSING["ARROWSLITS"]
    server, g = setup(3)
    g.data["players"]["1"]["civ"] = "GOTHS"
    train.open_menu(g, "Steve", (9, 9))
    assert ":book:Arrowslits:" not in menus(server)[-1]


def test_the_values_of_architecture_and_arrowslits():
    _, g = setup(3)
    g.techs |= {"MASONRY", "ARCHITECTURE"}
    assert build.values(g, "HOUSE")[:4] == (666, 0, 2, 9)               # 550 × 1.1 × 1.1, +2/+2 armor
    assert build.values(g, "STONE_WALL") == combat.stats("STONE_WALL")  # no change for walls and gates
    g.techs = set(build.AGE_TECHS[:3]) | {"ARROWSLITS"}
    assert build.values(g, "WATCH_TOWER").attack == 5 + 1
    g.techs.add("GUARD_TOWER")
    assert build.values(g, "WATCH_TOWER").attack == 7 + 2
    g.techs.add("KEEP")
    assert build.values(g, "WATCH_TOWER").attack == 8 + 3
    assert build.values(g, "TOWN_CENTER") == build.values(g, "TOWN_CENTER", set(build.AGE_TECHS[:3]))


def test_the_research_changes_the_own_buildings():
    server, g = setup(3)
    g.techs.add("MASONRY")
    server.hp[uuid(MAP)], server.hp[uuid(TC)] = 622, 2640             # the tower lost 500 hit points
    research(g, "ARCHITECTURE", 70)
    assert server.hp[uuid(MAP)] == 1234 - 500 and server.hp[uuid(TC)] == 2904
    assert any(c.startswith(f"aoe building {uuid(MAP)} 1234 3 9 ") for c in server.log)
    server.log.clear()
    g.stock.update(food=600, wood=600)
    research(g, "ARROWSLITS", 25)
    assert any(c.startswith(f"aoe building {uuid(MAP)} 1234 3 9 ") for c in server.log)
    assert build.values(g, "WATCH_TOWER").attack == 5 + 1
