"""Heavy Warships upgrades the war hulk to the carrack (#1933, AoE2 DE wiki "Carrack (unit)", The Last Chieftains): the
live war hulks get the name and the values of the carrack, and the dock trains the carrack in the slot of the hulk
(train.MORE + 2). Fake server."""
from test_dock_train import DOCK
from test_heavy_warships import imperial
from test_train_archery import menus

import units
from game import combat, train


def test_the_carrack_has_the_aoe2_de_values_of_the_wiki():
    assert "CARRACK" in combat.MELEE_RANGED and "CARRACK" in train.HULKS and len(train.HELP["HEAVY_WARSHIPS"]) <= 50
    assert units.classify("CARRACK") == units.classify("WAR_HULK")         # a dark oak boat with two crew


def test_heavy_warships_upgrades_the_live_war_hulk_and_the_dock_trains_the_carrack():
    server, g = imperial(techs=["MEDIUM_WARSHIPS"])
    g.data["players"]["1"]["civ"] = "FRANKS"
    g.soldiers |= {"h": "WAR_HULK"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    train.open_menu(g, "Steve", (15, 12))
    assert f" {train.MORE + 2}:dark_oak_boat:War Hulk:" in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, 3) == 1
    train.tick(g, 65)
    assert "HEAVY_WARSHIPS" in g.techs and g.soldiers["h"] == "CARRACK"
    assert combat.stats_command("h", "CARRACK") in server.log and combat.label_command("h", "CARRACK") in server.log
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert f" {train.MORE + 2}:dark_oak_boat:Carrack:75 wood · 35 gold · 27 s · queue 0/15" in menu
    assert ":War Hulk:" not in menu
    assert train.order(g, "Steve", DOCK, train.MORE + 2) == 1
    uuid, = train.tick(g, 27)
    assert g.soldiers[uuid] == "CARRACK" and uuid in g.ships


def test_the_blacksmith_attack_upgrades_add_attack_to_the_carrack():
    server, g = imperial()
    base = combat.stats("CARRACK").attack
    for techs, n in ((["FORGING"], 1), (["FORGING", "IRON_CASTING"], 2), (["FORGING", "IRON_CASTING", "BLAST_FURNACE"], 4)):
        g.techs |= set(techs)
        assert train.stats(g, "CARRACK").attack == base + n
