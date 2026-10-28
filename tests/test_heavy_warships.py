"""The dock researches the Demolition Ship upgrade in the Castle Age, and Heavy Warships and Heavy Demolition Ship in the
Imperial Age (#1483). Then the live ships of each line get the new name and values, and the dock trains the new form in
the slot of the old one. AoE2 DE values: the wiki infoboxes (MediaWiki API, 2026-10-27) "Fire Ship" (UpCost of Heavy
Warships 400 wood, 315 gold, 65 s), "Demolition Raft" (UpCost 25 wood, 75 gold, 20 s), "Demolition Ship" (UpCost 200
wood, 300 gold, 50 s), "Galleon", "Fast Fire Ship" and "Heavy Demolition Ship", and their availability charts."""
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

from game import build, civs, combat, fleet, train

TECHS = {"DEMOLITION_SHIP_UPGRADE": ({"wood": 25, "gold": 75}, 20, 2), "HEAVY_WARSHIPS": ({"wood": 400, "gold": 315}, 65, 3),
         "HEAVY_DEMOLITION_SHIP_UPGRADE": ({"wood": 200, "gold": 300}, 50, 3)}


def imperial(civ="BRITONS", techs=()):
    server, g = dock_map(wood=2000)
    g.techs |= set(build.AGE_TECHS[:3]) | set(techs)
    g.stock["gold"] = 2000
    g.data["players"]["1"]["civ"] = civ
    return server, g


def test_the_values_are_those_of_aoe2_de():
    for t, (cost, time, age) in TECHS.items():
        assert (train.COSTS[t], train.TRAIN_TIMES[t], train.BY_KEY["age"][t]) == (cost, time, age), t
        assert len(train.HELP[t]) <= 50 and t in train.TRAINS["DOCK"]
    assert train.BY_KEY["after"]["HEAVY_WARSHIPS"] == "MEDIUM_WARSHIPS"
    assert train.BY_KEY["after"]["HEAVY_DEMOLITION_SHIP_UPGRADE"] == "DEMOLITION_SHIP_UPGRADE"
    assert train.lines("HEAVY_WARSHIPS") == (("WAR_GALLEY", "GALLEON"), ("FIRE_SHIP", "DRAGON_SHIP"),
                                            ("FIRE_SHIP", "FAST_FIRE_SHIP"), ("WAR_HULK", "CARRACK"))
    assert [fleet.SPEEDS[n] for n in ("GALLEON", "FAST_FIRE_SHIP", "HEAVY_DEMOLITION_SHIP")] == [1.36, 1.56, 1.52]
    assert [combat.sight(n) for n in ("GALLEON", "FAST_FIRE_SHIP", "HEAVY_DEMOLITION_SHIP")] == [9, 6, 6]
    assert combat.range_command("u", "HEAVY_DEMOLITION_SHIP", 4) == "aoe range u 4.0 1 13.0"   # 3.25 tiles of blast
    assert combat.damage("FAST_FIRE_SHIP", "GALLEON") == 4 - 0 + 1 and "FAST_FIRE_SHIP" in combat.MELEE_RANGED
    assert set(civs.MISSING["GALLEON"]) == {"AZTECS", "KHITANS", "MALIANS"}
    assert {"VIKINGS", "SAXONS"} <= set(civs.MISSING["FAST_FIRE_SHIP"]) and "AZTECS" not in civs.MISSING["FAST_FIRE_SHIP"]
    assert "BRITONS" not in civs.MISSING["HEAVY_DEMOLITION_SHIP"] and "KOREANS" in civs.MISSING["HEAVY_DEMOLITION_SHIP"]


def test_the_demolition_ship_needs_its_upgrade_in_the_castle_age():
    server, g = dock_map(wood=400)
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    g.stock["gold"] = 300
    g.soldiers["raft"] = "DEMOLITION_RAFT"
    g.game.entities.setdefault("raft", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert "4:book:Demolition Ship:25 wood · 75 gold · 20 s · research" in menu
    assert "7:bamboo_raft:Demolition Raft:" in menu and ":Demolition Ship:45" not in menu
    assert train.order(g, "Steve", DOCK, 4) == 1
    train.tick(g, 20)
    assert "DEMOLITION_SHIP_UPGRADE" in g.techs and g.soldiers["raft"] == "DEMOLITION_SHIP"
    assert combat.range_command("raft", "DEMOLITION_SHIP", 1) in server.log
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert "7:bamboo_raft:Demolition Ship:45 wood · 80 gold · 31 s · queue 0/15" in menu and "Demolition Raft" not in menu
    assert "Heavy Demolition Ship" not in menu                          # the Imperial Age


def test_heavy_warships_and_heavy_demolition_ship_upgrade_the_live_ships():
    server, g = imperial(techs=["MEDIUM_WARSHIPS", "DEMOLITION_SHIP_UPGRADE"])
    g.soldiers |= {"war": "WAR_GALLEY", "fire": "FIRE_SHIP", "demo": "DEMOLITION_SHIP", "fish": "FISHING_SHIP"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert "3:book:Heavy Warships:400 wood · 315 gold · 65 s · research" in menu
    assert "4:book:Heavy Demolition Ship:200 wood · 300 gold · 50 s · research" in menu
    assert train.order(g, "Steve", DOCK, 3) == 1 and train.order(g, "Steve", DOCK, 4) == 1
    train.tick(g, 65)
    train.tick(g, 50)
    assert {"HEAVY_WARSHIPS", "HEAVY_DEMOLITION_SHIP_UPGRADE"} <= g.techs
    assert [g.soldiers[u] for u in ("war", "fire", "demo", "fish")] == \
        ["GALLEON", "FAST_FIRE_SHIP", "HEAVY_DEMOLITION_SHIP", "FISHING_SHIP"]
    assert combat.stats_command("war", "GALLEON", train.stats(g, "GALLEON")) in server.log
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert "1:dark_oak_boat:Galleon:90 wood · 30 gold · 27 s · queue 0/15" in menu
    assert "6:mangrove_boat:Fast Fire Ship:75 wood · 45 gold · 27 s · queue 0/15" in menu
    assert "7:bamboo_raft:Heavy Demolition Ship:45 wood · 80 gold · 31 s · queue 0/15" in menu
    assert "War Galley" not in menu and ":Fire Ship:" not in menu and "Heavy Warships" not in menu
    assert train.order(g, "Steve", DOCK, 1) == 1
    galleon, = train.tick(g, 27)
    assert g.soldiers[galleon] == "GALLEON" and galleon in g.ships


def test_a_civilization_gets_only_the_new_ships_that_it_has():
    server, g = imperial("VIKINGS", ["MEDIUM_WARSHIPS", "DEMOLITION_SHIP_UPGRADE"])   # no fast fire ship, no demolition ships
    g.soldiers |= {"war": "WAR_GALLEY", "fire": "FIRE_SHIP"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert "Heavy Warships" in menu and "Heavy Demolition Ship" not in menu and "Demolition" not in menu
    assert train.order(g, "Steve", DOCK, 3) == 1
    train.tick(g, 65)
    assert (g.soldiers["war"], g.soldiers["fire"]) == ("GALLEON", "FIRE_SHIP")
    train.open_menu(g, "Steve", (15, 12))
    assert "6:mangrove_boat:Fire Ship:" in menus(server)[-1] and "Fast Fire Ship" not in menus(server)[-1]
    server, g = imperial("AZTECS", ["MEDIUM_WARSHIPS", "HEAVY_WARSHIPS"])   # no galleon, a fast fire ship
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert "1:dark_oak_boat:War Galley:" in menu and ":Galleon:" not in menu and "Fast Fire Ship" in menu
