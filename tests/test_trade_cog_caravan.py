"""game/fleet.py and game/train.py: after Caravan an own trade cog sails faster, as in AoE2 DE (wiki "Trade Cog" and
"Caravan (Age of Empires II)", MediaWiki API, 2026-10-27, #1497).
Other ships do not change."""
from test_trade_cog import HOME, docks_map

from game import civs, fleet, train


def test_caravan_makes_the_trade_cog_and_the_trade_cart_faster():
    server, g = docks_map()
    cog = fleet.speed("TRADE_COG", 1, g)
    assert cog == fleet.SPEEDS["TRADE_COG"]
    g.techs.add("CARAVAN")
    assert fleet.speed("TRADE_COG", 1, g) > cog
    assert fleet.speed("TRADE_COG", 4) == cog * 4                            # no player: the base speed
    for name in ("GALLEY", "TRANSPORT_SHIP", "FISHING_SHIP"):
        assert fleet.speed(name, 1, g) == fleet.SPEEDS[name], name
    assert train.speed(g, "TRADE_CART") > 1 and train.speed(g, "MONK") == 1
    assert civs.GROUPS["trade units"]("TRADE_COG", None)


def test_a_trade_cog_after_caravan_sails_more_cells_in_the_same_time():
    sailed = {}
    for techs in ((), ("CARAVAN",)):
        server, g = docks_map()
        g.techs |= set(techs)
        train.open_menu(g, "Steve", (15, 3))
        assert train.order(g, "Steve", HOME, train.ITEMS["TRADE_COG"][0]) == 1
        cog, = train.tick(g, train.TRAIN_TIMES["TRADE_COG"])
        v = g.ships[cog]
        v.path = [(v.cell[0], v.cell[1] + k) for k in range(1, 31)]   # a straight line on the water
        fleet.tick(g, 10.0)
        sailed[techs] = 30 - len(v.path)
    assert sailed[("CARAVAN",)] > sailed[()] > 0
