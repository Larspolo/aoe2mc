"""The market actions of the AoE2 wiki (#1765, epic #1250): the market buys and sells each commodity, and each action
that the game program does not have is in EXCLUDED with the text that excludes it."""
from test_train import setup

from game import market

EXCLUDED = {
    "tribute": "Epic #1250: \"Out of this epic: the tribute of resources to other players (roadmap `play:diplomacy`)\"",
    "allied vision": "Epic #1250: the whole goal is \"build, buy, sell, train the trade cart, each technology of the "
                     "market\"; the allied vision is a game setting since patch 5.7 (wiki), not a market action",
}


def test_the_market_buys_and_sells_each_commodity():
    server, g = setup()
    g.stock["gold"] = 1000
    texts = [t for _, _, t, _ in market.items(g)]
    assert texts == [f"Buy {market.LOT} {r}" for r in market.RATES] + [f"Sell {market.LOT} {r}" for r in market.RATES]
    for r in market.RATES:
        g.stock[r] = market.LOT
        assert market.trade(g, "Steve", r, True) is True and market.trade(g, "Steve", r, False) is True


def test_each_excluded_item_names_its_source():
    assert all(v.startswith("Epic #1250") for v in EXCLUDED.values())
    assert not set(EXCLUDED) & set(market.RATES)
