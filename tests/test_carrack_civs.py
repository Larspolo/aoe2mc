"""The civilizations without the carrack keep the war hulk after Heavy Warships (#2077, AoE2 DE wiki "Carrack (unit)",
availability chart). Fake server."""
from test_carrack import DOCK, imperial, menus

from game import train

NO_CARRACK = {"BRITONS", "DANES", "GEORGIANS", "HUNS", "MONGOLS", "ROMANS", "TUPI"}


def test_the_civilizations_without_the_carrack():
    assert set(train.civs.MISSING["CARRACK"]) == NO_CARRACK


def test_a_briton_war_hulk_stays_a_war_hulk_after_heavy_warships():
    server, g = imperial(techs=["MEDIUM_WARSHIPS"])
    g.data["players"]["1"]["civ"] = "BRITONS"
    g.soldiers |= {"h": "WAR_HULK"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    assert train.order(g, "Steve", DOCK, 3) == 1
    train.tick(g, 65)
    assert "HEAVY_WARSHIPS" in g.techs and g.soldiers["h"] == "WAR_HULK"
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert f" {train.MORE + 2}:dark_oak_boat:War Hulk:" in menu and ":Carrack:" not in menu
