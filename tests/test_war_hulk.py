"""Medium Warships upgrades the hulk to the war hulk (#1508, AoE2 DE wiki "War Hulk", The Last Chieftains): the live
hulks get the name and the values of the war hulk, and the dock trains the war hulk in the slot of the hulk
(train.MORE + 2). Fake server."""
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

import units
from game import combat, train


def test_the_war_hulk_has_the_aoe2_de_values_of_the_wiki():
    assert "WAR_HULK" in combat.MELEE_RANGED and len(train.HELP["WAR_HULK"]) <= 50
    assert ("HULK", "WAR_HULK") in train.lines("MEDIUM_WARSHIPS")
    assert units.classify("WAR_HULK") == units.classify("WAR_GALLEY")      # a dark oak boat with two crew


def test_medium_warships_upgrades_the_live_hulk_and_the_dock_trains_the_war_hulk():
    server, g = dock_map(wood=400)
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    g.stock["gold"] = 300
    g.soldiers |= {"h": "HULK"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    train.open_menu(g, "Steve", (15, 12))
    assert f" {train.MORE + 2}:oak_boat:Hulk:" in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, 3) == 1
    train.tick(g, 50)
    assert "MEDIUM_WARSHIPS" in g.techs and g.soldiers["h"] == "WAR_HULK"
    assert combat.stats_command("h", "WAR_HULK") in server.log and combat.label_command("h", "WAR_HULK") in server.log
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert f" {train.MORE + 2}:dark_oak_boat:War Hulk:75 wood · 35 gold · 27 s · queue 0/15" in menu
    assert ":Hulk:" not in menu
    assert train.order(g, "Steve", DOCK, train.MORE + 2) == 1
    uuid, = train.tick(g, 27)
    assert g.soldiers[uuid] == "WAR_HULK" and uuid in g.ships
