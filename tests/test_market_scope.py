"""The full list of the market actions of the AoE2 wiki (#1765, epic #1250): each one is in the game program, or in
EXCLUDED with the text that excludes it. A removed item fails here."""
from test_train import setup

from game import build, market, train

# AoE2 wiki "Market (Age of Empires II)", revision 1088855 (infobox "Use", "Exchange of resources"), and its template
# "Market Tech Tree (Age of Empires II)", revision 1027366 (MediaWiki API, 2026-10-27).
BUILD = {"MARKET": ({"wood": 175}, 60, 1)}                          # 175 wood, 60 seconds, the Feudal Age
EXCHANGE = ("food", "wood", "stone")                               # "exchanges the three commodities ... for gold"
UNITS = ("TRADE_CART",)
TECHS = ("COINAGE", "BANKING", "CARAVAN", "GUILDS")
EXCLUDED = {
    "tribute": "Epic #1250: \"Out of this epic: the tribute of resources to other players (roadmap `play:diplomacy`)\"",
    "allied vision": "Epic #1250: the whole goal is \"build, buy, sell, train the trade cart, each technology of the "
                     "market\"; the allied vision is a game setting since patch 5.7 (wiki), not a market action",
}


def test_the_player_builds_the_market_with_the_wiki_values():
    for name, (cost, seconds, age) in BUILD.items():
        assert (build.COSTS[name], build.BUILD_TIMES[name], build.AGE[name]) == (cost, seconds, age)


def test_the_market_buys_and_sells_each_commodity():
    server, g = setup()
    g.stock["gold"] = 1000
    texts = [t for _, _, t, _ in market.items(g)]
    assert texts == [f"Buy {market.LOT} {r}" for r in market.RATES] + [f"Sell {market.LOT} {r}" for r in market.RATES]
    assert sorted(market.RATES) == sorted(EXCHANGE)
    for r in EXCHANGE:
        g.stock[r] = market.LOT
        assert market.trade(g, "Steve", r, True) is True and market.trade(g, "Steve", r, False) is True


def test_the_market_trains_each_unit_and_technology_of_the_wiki():
    assert set(train.TRAINS["MARKET"]) == set(UNITS) | set(TECHS)


def test_each_excluded_item_names_its_source():
    assert all(v.startswith("Epic #1250") for v in EXCLUDED.values())
    assert not set(EXCLUDED) & {*BUILD, *EXCHANGE, *UNITS, *TECHS}
