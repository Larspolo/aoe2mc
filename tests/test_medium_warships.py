"""Medium Warships (#1482): the dock researches it in the Castle Age (150 wood, 100 gold, 50 s; AoE2 wiki "Medium
Warships"). Then the live galleys become war galleys and the fire galleys fire ships, and the dock trains the new
forms in their slots. The fire ship needs it ("TrainReq"). The hulk becomes the war hulk: tests/test_war_hulk.py."""
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

from game import combat, train


def castle(wood=400, gold=300):
    server, g = dock_map(wood=wood)
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    g.stock["gold"] = gold
    return server, g


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["MEDIUM_WARSHIPS"]) <= 50
    assert train.lines("MEDIUM_WARSHIPS") == (("GALLEY", "WAR_GALLEY"), ("FIRE_GALLEY", "FIRE_SHIP"), ("HULK", "WAR_HULK"))
    assert train.lines("MAN_AT_ARMS_UPGRADE") == (("MILITIA", "MAN_AT_ARMS"),)
    assert "FIRE_SHIP" not in train.TRAINS["DOCK"]


def test_the_dock_menu_shows_it_in_the_castle_age_and_no_fire_ship_before_it():
    server, g = dock_map()
    g.techs = {"FEUDAL_AGE"}
    train.open_menu(g, "Steve", (15, 12))
    assert "Medium Warships" not in menus(server)[-1] and "Fire Ship" not in menus(server)[-1]
    server, g = castle()
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert " 3:book:Medium Warships:150 wood · 100 gold · 50 s · research" in menu
    assert "1:oak_boat:Galley:" in menu and "6:mangrove_boat:Fire Galley:" in menu and "Fire Ship" not in menu


def test_the_research_upgrades_the_live_ships_and_the_dock_trains_the_new_forms():
    server, g = castle()
    g.soldiers |= {"gal": "GALLEY", "fg": "FIRE_GALLEY", "fs": "FISHING_SHIP"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (15, 12)), 3) == 1
    assert (g.stock["wood"], g.stock["gold"]) == (250, 200)
    train.tick(g, 49)
    assert "MEDIUM_WARSHIPS" not in g.techs and g.soldiers["gal"] == "GALLEY"
    train.tick(g, 1)
    assert "MEDIUM_WARSHIPS" in g.techs
    assert (g.soldiers["gal"], g.soldiers["fg"], g.soldiers["fs"]) == ("WAR_GALLEY", "FIRE_SHIP", "FISHING_SHIP")
    assert combat.stats_command("gal", "WAR_GALLEY") in server.log and combat.label_command("fg", "FIRE_SHIP") in server.log
    assert combat.range_command("gal", "WAR_GALLEY", 1) in server.log
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert "1:dark_oak_boat:War Galley:90 wood · 30 gold · 27 s · queue 0/15" in menu
    assert "6:mangrove_boat:Fire Ship:75 wood · 45 gold · 27 s · queue 0/15" in menu
    assert ":Galley:" not in menu and "Fire Galley" not in menu and "Medium Warships" not in menu
    assert train.order(g, "Steve", DOCK, 1) == 1 and train.order(g, "Steve", DOCK, 6) == 1
    war, = train.tick(g, 27)
    fire, = train.tick(g, 27)
    assert (g.soldiers[war], g.soldiers[fire]) == ("WAR_GALLEY", "FIRE_SHIP") and war in g.ships and fire in g.ships
