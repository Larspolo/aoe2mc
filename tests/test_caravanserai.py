"""game/build.py, game/trade.py: the Hindustanis and the Persians build the Caravanserai in the Imperial Age (#2341,
AoE2 DE wiki "Caravanserai (Age of Empires II)"). The trade carts of its player and its allies walk faster in its aura,
a square some tiles from each edge (trade.AURAS)."""
from test_build_menu import villager_map
from test_krepost import shown
from test_trade_legs import setup

from game import ai, build, civs, trade, train

SERAI = [150, 150, 154, 154]                                           # x0, z0, x1, z1 (tile size 1)
SPEED, TILES = trade.AURAS["CARAVANSERAI"]


def test_only_a_hindustani_or_persian_player_has_the_caravanserai_in_the_menu():
    server, g = villager_map()                                         # Britons
    build.open_menu(g, "Steve")
    assert ("Caravanserai" in shown(server)) == ("BRITONS" in civs.ONLY["CARAVANSERAI"])
    for civ in sorted(civs.ONLY["CARAVANSERAI"]):
        g.data["players"]["1"]["civ"] = civ
        build.open_menu(g, "Steve")
        assert "Caravanserai" in shown(server)
        item = next(it for it in build.items(g) if it[2] == "Caravanserai")
        assert item[3].endswith("Needs the Imperial Age")


def serai(player=1, players=None):
    """The trade map of test_trade_legs with a Caravanserai of player (start building) and the players."""
    server, g = setup()
    g.data["objects"].append({"kind": "building", "name": "CARAVANSERAI", "player": player, "footprint": SERAI})
    g.players = players or {}
    return server, g


def test_a_cart_in_the_aura_walks_faster():
    server, g = serai()
    assert trade.aura(g, (152, 152)) == SPEED                         # inside the building
    a, b = 150 - TILES, 153 + TILES                                    # TILES from the edges: a square
    assert trade.aura(g, (a, a)) == trade.aura(g, (b, b)) == SPEED
    assert trade.aura(g, (a - 1, 152)) == trade.aura(g, (b + 1, 152)) == trade.aura(g, (152, a - 30)) == 1.0
    trade.leg(g, "c", (b - 1, 145))
    fast = ai.speed_command("c", trade.CART, 1, ai.NORMAL * train.speed(g, trade.CART) * SPEED)
    assert server.log[-2:] == [fast, f"aoe moveto c {b - 0.5} 64 145.5"]
    trade.leg(g, "c", (100, 100))
    assert server.log[-2] == ai.speed_command("c", trade.CART, 1, ai.NORMAL * train.speed(g, trade.CART))


def test_the_aura_counts_for_allies_not_for_enemies_and_not_for_a_site():
    assert trade.aura(serai(2)[1], (152, 152)) == 1.0                  # an enemy: no team
    team = {"1": {"team": 1}, "2": {"team": 1}}
    assert trade.aura(serai(2, team)[1], (152, 152)) == SPEED          # an ally
    server, g = setup()
    g.sites.append({"name": "CARAVANSERAI", "player": 1, "footprint": (150, 154, 150, 154)})
    assert trade.aura(g, (152, 152)) == 1.0                            # not complete
    g.sites[-1]["done"] = True
    assert trade.aura(g, (152, 152)) == SPEED
