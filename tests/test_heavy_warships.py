"""The dock researches the Demolition Ship upgrade in the Castle Age, and Heavy Warships and Heavy Demolition Ship in the
Imperial Age (#1483). Then the live ships of each line get the new name and values, and the dock trains the new form in
the slot of the old one. AoE2 DE values: the wiki infoboxes (MediaWiki API, 2026-10-27) "Fire Ship", "Demolition Raft",
"Demolition Ship", "Galleon", "Fast Fire Ship" and "Heavy Demolition Ship", and their availability charts."""
from menu_line import item
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

from game import build, combat, train


def slot(menu, label):
    return int(item(menu, label).split(":")[0])


def imperial(civ="BRITONS", techs=()):
    server, g = dock_map(wood=2000)
    g.techs |= set(build.AGE_TECHS[:3]) | set(techs)
    g.stock["gold"] = 2000
    g.data["players"]["1"]["civ"] = civ
    return server, g


def test_the_demolition_ship_needs_its_upgrade_in_the_castle_age():
    server, g = dock_map(wood=2000)
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    g.stock["gold"] = 2000
    g.soldiers["raft"] = "DEMOLITION_RAFT"
    g.game.entities.setdefault("raft", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert item(menu, "Demolition Ship").endswith(" · research") and item(menu, "Demolition Raft")
    assert train.order(g, "Steve", DOCK, slot(menu, "Demolition Ship")) == 1
    train.tick(g, train.seconds(g, "DEMOLITION_SHIP_UPGRADE", "DOCK"))
    assert "DEMOLITION_SHIP_UPGRADE" in g.techs and g.soldiers["raft"] == "DEMOLITION_SHIP"
    assert combat.range_command("raft", "DEMOLITION_SHIP", 1) in server.log
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert item(menu, "Demolition Ship").endswith(" · queue 0/15") and "Demolition Raft" not in menu
    assert "Heavy Demolition Ship" not in menu                          # the Imperial Age


def test_heavy_warships_and_heavy_demolition_ship_upgrade_the_live_ships():
    server, g = imperial(techs=["MEDIUM_WARSHIPS", "DEMOLITION_SHIP_UPGRADE"])
    g.soldiers |= {"war": "WAR_GALLEY", "fire": "FIRE_SHIP", "demo": "DEMOLITION_SHIP", "fish": "FISHING_SHIP"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert item(menu, "Heavy Warships").endswith(" · research")
    assert item(menu, "Heavy Demolition Ship").endswith(" · research")
    assert train.order(g, "Steve", DOCK, slot(menu, "Heavy Warships")) == 1
    assert train.order(g, "Steve", DOCK, slot(menu, "Heavy Demolition Ship")) == 1
    train.tick(g, train.seconds(g, "HEAVY_WARSHIPS", "DOCK"))
    train.tick(g, train.seconds(g, "HEAVY_DEMOLITION_SHIP_UPGRADE", "DOCK"))
    assert {"HEAVY_WARSHIPS", "HEAVY_DEMOLITION_SHIP_UPGRADE"} <= g.techs
    assert [g.soldiers[u] for u in ("war", "fire", "demo", "fish")] == \
        ["GALLEON", "FAST_FIRE_SHIP", "HEAVY_DEMOLITION_SHIP", "FISHING_SHIP"]
    assert combat.stats_command("war", "GALLEON", train.stats(g, "GALLEON")) in server.log
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert all(item(menu, n).endswith(" · queue 0/15") for n in ("Galleon", "Fast Fire Ship", "Heavy Demolition Ship"))
    assert "War Galley" not in menu and ":Fire Ship:" not in menu and "Heavy Warships" not in menu
    assert train.order(g, "Steve", DOCK, slot(menu, "Galleon")) == 1
    galleon, = train.tick(g, train.seconds(g, "GALLEON", "DOCK"))
    assert g.soldiers[galleon] == "GALLEON" and galleon in g.ships


def test_a_civilization_gets_only_the_new_ships_that_it_has():
    server, g = imperial("VIKINGS", ["MEDIUM_WARSHIPS", "DEMOLITION_SHIP_UPGRADE"])   # no fast fire ship, no demolition ships
    g.soldiers |= {"war": "WAR_GALLEY", "fire": "FIRE_SHIP"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert "Heavy Warships" in menu and "Heavy Demolition Ship" not in menu and "Demolition" not in menu
    assert train.order(g, "Steve", DOCK, slot(menu, "Heavy Warships")) == 1
    train.tick(g, train.seconds(g, "HEAVY_WARSHIPS", "DOCK"))
    assert (g.soldiers["war"], g.soldiers["fire"]) == ("GALLEON", "FIRE_SHIP")
    train.open_menu(g, "Steve", (15, 12))
    assert item(menus(server)[-1], "Fire Ship") and "Fast Fire Ship" not in menus(server)[-1]
    server, g = imperial("AZTECS", ["MEDIUM_WARSHIPS", "HEAVY_WARSHIPS"])   # no galleon, a fast fire ship
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert item(menu, "War Galley") and ":Galleon:" not in menu and "Fast Fire Ship" in menu
