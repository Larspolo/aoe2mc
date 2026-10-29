"""The civilizations without the carrack keep the war hulk after Heavy Warships (#2077, AoE2 DE wiki "Carrack (unit)",
availability chart). Fake server."""
from test_carrack import DOCK, imperial, menus

from game import train

def test_a_war_hulk_without_the_carrack_stays_a_war_hulk_after_heavy_warships():
    server, g = imperial(techs=["MEDIUM_WARSHIPS"])
    g.data["players"]["1"]["civ"] = sorted(train.civs.MISSING["CARRACK"])[0]
    g.soldiers |= {"h": "WAR_HULK"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    assert train.order(g, "Steve", DOCK, train.layout(g, DOCK)["HEAVY_WARSHIPS"][0]) == 1
    train.tick(g, train.seconds(g, "HEAVY_WARSHIPS"))
    assert "HEAVY_WARSHIPS" in g.techs and g.soldiers["h"] == "WAR_HULK"
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert ":War Hulk:" in menu and ":Carrack:" not in menu
