"""Medium Warships (#1482): the dock researches it in the Castle Age. Then the live galleys become war galleys and the
fire galleys fire ships, and the dock trains the new forms in their slots. The fire ship needs it ("TrainReq"). The
hulk becomes the war hulk: tests/test_war_hulk.py."""
from menu_line import item
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

from game import combat, train


def castle(wood=400, gold=300):
    server, g = dock_map(wood=wood)
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    g.stock["gold"] = gold
    return server, g


def test_the_dock_menu_shows_it_in_the_castle_age_and_no_fire_ship_before_it():
    server, g = dock_map()
    g.techs = {"FEUDAL_AGE"}
    train.open_menu(g, "Steve", (15, 12))
    assert "Medium Warships" not in menus(server)[-1] and "Fire Ship" not in menus(server)[-1]
    server, g = castle()
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert item(menu, "Medium Warships").endswith(" · research")
    assert item(menu, "Galley") and item(menu, "Fire Galley") and "Fire Ship" not in menu


def test_the_research_upgrades_the_live_ships_and_the_dock_trains_the_new_forms():
    server, g = castle()
    g.soldiers |= {"gal": "GALLEY", "fg": "FIRE_GALLEY", "fs": "FISHING_SHIP"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    cost, t = train.price(g, "MEDIUM_WARSHIPS"), train.seconds(g, "MEDIUM_WARSHIPS", "DOCK")
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (15, 12)), train.SLOTS["MEDIUM_WARSHIPS"]) == 1
    assert (g.stock["wood"], g.stock["gold"]) == (400 - cost.get("wood", 0), 300 - cost.get("gold", 0))
    train.tick(g, t - 1)
    assert "MEDIUM_WARSHIPS" not in g.techs and g.soldiers["gal"] == "GALLEY"
    train.tick(g, 1)
    assert "MEDIUM_WARSHIPS" in g.techs
    new = dict(train.lines("MEDIUM_WARSHIPS"))
    assert (g.soldiers["gal"], g.soldiers["fg"], g.soldiers["fs"]) == (new["GALLEY"], new["FIRE_GALLEY"], "FISHING_SHIP")
    assert combat.stats_command("gal", "WAR_GALLEY") in server.log and combat.label_command("fg", "FIRE_SHIP") in server.log
    assert combat.range_command("gal", "WAR_GALLEY", 1) in server.log
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    slots = [int(item(menu, label).split(":")[0]) for label in ("War Galley", "Fire Ship")]
    assert all(item(menu, label).endswith("queue 0/15") for label in ("War Galley", "Fire Ship"))
    assert ":Galley:" not in menu and "Fire Galley" not in menu and "Medium Warships" not in menu
    assert train.order(g, "Steve", DOCK, slots[0]) == 1 and train.order(g, "Steve", DOCK, slots[1]) == 1
    war, = train.tick(g, train.seconds(g, "WAR_GALLEY", "DOCK"))
    fire, = train.tick(g, train.seconds(g, "FIRE_SHIP", "DOCK"))
    assert (g.soldiers[war], g.soldiers[fire]) == ("WAR_GALLEY", "FIRE_SHIP") and war in g.ships and fire in g.ships
