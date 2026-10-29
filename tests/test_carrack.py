"""Heavy Warships upgrades the war hulk to the carrack (#1933, AoE2 DE wiki "Carrack (unit)", The Last Chieftains): the
live war hulks get the name and the values of the carrack, and the dock trains the carrack in the slot of the hulk.
Fake server."""
from test_castle_upgrades import entry
from test_dock_train import DOCK
from test_heavy_warships import imperial
from test_train_archery import menus

from game import combat, train


def test_the_help_text_is_short():
    assert len(train.HELP["HEAVY_WARSHIPS"]) <= 50


def test_heavy_warships_upgrades_the_live_war_hulk_and_the_dock_trains_the_carrack():
    server, g = imperial(techs=["MEDIUM_WARSHIPS"])
    g.data["players"]["1"]["civ"] = "FRANKS"
    g.soldiers |= {"h": "WAR_HULK"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    train.open_menu(g, "Steve", (15, 12))
    slot = entry(g, (15, 12), "WAR_HULK").split(":")[0]
    assert " " + entry(g, (15, 12), "WAR_HULK") in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, train.layout(g, DOCK)["HEAVY_WARSHIPS"][0]) == 1
    train.tick(g, train.seconds(g, "HEAVY_WARSHIPS"))
    assert "HEAVY_WARSHIPS" in g.techs and g.soldiers["h"] == "CARRACK"
    assert combat.stats_command("h", "CARRACK") in server.log and combat.label_command("h", "CARRACK") in server.log
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert " " + entry(g, (15, 12), "CARRACK") + "queue 0/15" in menu
    assert entry(g, (15, 12), "CARRACK").split(":")[0] == slot and ":War Hulk:" not in menu   # the slot of the hulk
    assert train.order(g, "Steve", DOCK, int(slot)) == 1
    uuid, = train.tick(g, train.seconds(g, "CARRACK"))
    assert g.soldiers[uuid] == "CARRACK" and uuid in g.ships


def test_the_blacksmith_attack_upgrades_add_attack_to_the_carrack():
    server, g = imperial()
    seen = [combat.stats("CARRACK").attack]
    for tech in ("FORGING", "IRON_CASTING", "BLAST_FURNACE"):
        g.techs.add(tech)
        seen.append(train.stats(g, "CARRACK").attack)
    assert all(a < b for a, b in zip(seen, seen[1:])), seen               # each one adds attack
