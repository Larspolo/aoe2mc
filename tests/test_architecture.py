"""game/train.py: the university researches Architecture (after Masonry) and Arrowslits in the Imperial Age, #1504.
Architecture: the buildings get more hit points and armor, as Masonry. Arrowslits: the towers get more attack."""
from menu_line import item
from test_loom import menus
from test_tower_upgrades import MAP, research, setup, uuid

from game import build, civs, combat, train

TC = (2, 5, 2, 5)


def text(g, name):
    """The cost and time text of the university menu item of name, from the data (as train.show writes it)."""
    return " · ".join(f"{v} {r}" for r, v in train.price(g, name).items()) + f" · {round(train.seconds(g, name), 1):g} s · "


def test_the_university_menu_shows_both_in_the_imperial_age_and_architecture_after_masonry():
    for age, shown in ((2, False), (3, True)):
        server, g = setup(age)
        train.open_menu(g, "Steve", (9, 9))
        assert (":book:Arrowslits:" in menus(server)[-1]) == shown
        assert ":book:Architecture:" not in menus(server)[-1]          # Masonry first
    assert item(menus(server)[-1], "Arrowslits").endswith(":Arrowslits:" + text(g, "ARROWSLITS") + "research")
    g.techs.add("MASONRY")
    train.open_menu(g, "Steve", (9, 9))
    assert item(menus(server)[-1], "Architecture").endswith(":Architecture:" + text(g, "ARCHITECTURE") + "research")


def test_a_civilization_without_the_technology_does_not_see_it():
    server, g = setup(3)
    g.data["players"]["1"]["civ"] = civs.MISSING["ARROWSLITS"][0]
    train.open_menu(g, "Steve", (9, 9))
    assert ":book:Arrowslits:" not in menus(server)[-1]


def test_the_values_of_architecture_and_arrowslits():
    _, g = setup(3)
    g.techs |= {"MASONRY", "ARCHITECTURE"}
    house, before = build.values(g, "HOUSE"), build.values(g, "HOUSE", g.techs - {"ARCHITECTURE"})
    assert house.hp > before.hp and house.melee > before.melee and house.pierce > before.pierce
    assert build.values(g, "STONE_WALL") == combat.stats("STONE_WALL")  # no change for walls and gates
    ages = set(build.AGE_TECHS[:3])
    for towers in ((), ("GUARD_TOWER",), ("GUARD_TOWER", "KEEP")):
        techs = ages | set(towers)
        assert build.values(g, "WATCH_TOWER", techs | {"ARROWSLITS"}).attack > build.values(g, "WATCH_TOWER", techs).attack
    g.techs = ages | {"ARROWSLITS", "GUARD_TOWER", "KEEP"}
    assert build.values(g, "TOWN_CENTER") == build.values(g, "TOWN_CENTER", set(build.AGE_TECHS[:3]))


def test_the_research_changes_the_own_buildings():
    server, g = setup(3)
    g.techs.add("MASONRY")
    tower, tc = build.values(g, "WATCH_TOWER").hp, build.values(g, "TOWN_CENTER").hp
    server.hp[uuid(MAP)], server.hp[uuid(TC)] = tower - 500, tc       # the tower lost 500 hit points
    research(g, "ARCHITECTURE")
    s = build.values(g, "WATCH_TOWER")
    assert s.hp > tower and server.hp[uuid(MAP)] == s.hp - 500 and server.hp[uuid(TC)] == build.values(g, "TOWN_CENTER").hp > tc
    assert any(c.startswith(f"aoe building {uuid(MAP)} {s.hp} ") for c in server.log)
    server.log.clear()
    g.stock.update(food=600, wood=600)
    research(g, "ARROWSLITS")
    assert any(c.startswith(f"aoe building {uuid(MAP)} {s.hp} ") for c in server.log)
    assert build.values(g, "WATCH_TOWER").attack > s.attack
