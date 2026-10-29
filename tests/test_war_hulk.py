"""Medium Warships upgrades the hulk to the war hulk (#1508, The Last Chieftains): the live hulks get the name and the
values of the war hulk, and the dock trains the war hulk in the slot of the hulk. Fake server."""
from test_dock_train import DOCK, dock_map
from test_train_archery import menus
from test_urumi_swordsman import item, label

from game import combat, train


def test_medium_warships_upgrades_the_live_hulk_and_the_dock_trains_the_war_hulk():
    server, g = dock_map(wood=400)
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    g.stock["gold"] = 300
    g.soldiers |= {"h": "HULK"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    train.open_menu(g, "Steve", (15, 12))
    slot, kind, name = train.ITEMS["HULK"]
    assert f" {slot}:{kind}:{name}:" in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, train.ITEMS["MEDIUM_WARSHIPS"][0]) == 1
    train.tick(g, train.seconds(g, "MEDIUM_WARSHIPS"))
    assert "MEDIUM_WARSHIPS" in g.techs and g.soldiers["h"] == "WAR_HULK"
    assert combat.stats_command("h", "WAR_HULK") in server.log and combat.label_command("h", "WAR_HULK") in server.log
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert item(g, "WAR_HULK", f"queue 0/{train.QUEUE}") in menu + " "
    assert f":{label('HULK')}:" not in menu
    assert train.order(g, "Steve", DOCK, train.ITEMS["WAR_HULK"][0]) == 1
    uuid, = train.tick(g, train.seconds(g, "WAR_HULK"))
    assert g.soldiers[uuid] == "WAR_HULK" and uuid in g.ships
