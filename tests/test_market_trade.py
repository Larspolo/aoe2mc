"""game/market.py: buy and sell wood, food and stone for gold at an own market, with the AoE2 DE prices (#1252).
Fake server. The values: the AoE2 wiki, "Market (Age of Empires II)": start rates 100 wood, 115 food, 130 stone (gold
per 100), a fee of 30 % (Guilds 15 %, Saracens 5 %), a step of 2 for each trade, rates from 20 to 9999."""
import shutil
from urllib.parse import unquote

import pytest
from menu_line import item
from test_train import setup
from test_train_menu import entry

from game import market

START = ("aoe menu Steve Market 0:oak_log:Buy 100 wood:130 gold 1:wheat:Buy 100 food:150 gold "
         "2:cobblestone:Buy 100 stone:169 gold 9:oak_log:Sell 100 wood:70 gold 10:wheat:Sell 100 food:81 gold "
         "11:cobblestone:Sell 100 stone:91 gold")
TRAIN = ("8:white_banner:Rally point:Click, then right click the ground", "18:oak_log:Buy 100 wood:130 gold",
         "19:wheat:Buy 100 food:150 gold", "20:cobblestone:Buy 100 stone:169 gold", "27:oak_log:Sell 100 wood:70 gold",
         "28:wheat:Sell 100 food:81 gold", "29:cobblestone:Sell 100 stone:91 gold")   # with the trade cart (#1253, #1286)


def market_map(**stock):
    """The map of test_train.setup with a market of player 1 in place of its town center (blocks x 2-4, z 2-4)."""
    server, g = setup()
    g.data["objects"][0]["name"] = "MARKET"
    g.stock.update(stock)
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_a_right_click_on_the_own_market_shows_the_buy_and_sell_prices():
    server, g = market_map()
    for name in g.clicks():
        g.click(name)
    cmd, = menus(server)
    assert cmd.startswith("aoe menu Steve Market ") and all(item(cmd, s.split(":")[2]) == s for s in TRAIN) and "Steve" in g.menus
    cart = entry(g, (2, 5, 2, 5), "TRADE_CART") + "Needs the Feudal Age"   # the cost and time of the data
    assert item(cmd, "Trade Cart") == cart
    g.stock.update(gold=1000, wood=0)
    g.menus["Steve"]("Steve", 18, False)                               # buy wood in the menu of the building
    assert g.stock["wood"] == 100 and item(menus(server)[-1], "Trade Cart") == cart
    assert market.open_menu(g, "Steve", (3, 3)) and menus(server)[-1].startswith(START[:40])


def test_no_market_menu_on_the_ground_or_at_a_market_of_another_player():
    server, g = market_map()
    g.data["objects"][1]["name"] = "MARKET"
    assert market.open_menu(g, "Steve", (18, 18)) is None and market.open_menu(g, "Steve", (10, 10)) is None
    assert market.open_menu(g, "Steve", (3, 3)) == (2, 5, 2, 5)


def test_a_built_market_has_the_menu_too():
    server, g = market_map()
    g.sites.append({"name": "MARKET", "player": 1, "footprint": (10, 13, 10, 13), "done": True})
    assert market.open_menu(g, "Steve", (11, 12)) == (10, 13, 10, 13)


def test_a_sequence_of_trades_follows_the_wiki_rule():
    server, g = market_map(gold=1000, wood=300)
    got = []
    for slot in (1, 1, 1, 9, 9):                                       # buy food 3 times, sell wood twice
        got.append(market.price(g, list(market.RATES)[slot % market.SELL], slot < market.SELL))
        assert market.order(g, "Steve", slot) == 1
    # food rate 115, 117, 119: 1.3 × rate rounded half up; wood rate 100, 98: 0.7 × rate
    assert got == [150, 152, 155, 70, 69]
    assert g.rates == {"wood": 96, "food": 121, "stone": 130}
    assert (g.stock["gold"], g.stock["food"], g.stock["wood"]) == (1000 - 457 + 139, 60 + 300, 100)
    assert "scoreboard players remove Gold aoe_res 150" in server.log and "scoreboard players add Food aoe_res 100" in server.log
    assert menus(server)[-1].endswith("9:oak_log:Sell 100 wood:67 gold 10:wheat:Sell 100 food:85 gold "
                                      "11:cobblestone:Sell 100 stone:91 gold")


def test_a_shift_click_trades_500_while_the_stock_allows():
    server, g = market_map(stone=350)
    assert market.order(g, "Steve", 11, shift=True) == 3               # 350 stone: 3 sells of 100
    assert g.stock["stone"] == 50 and g.rates["stone"] == 124 and g.stock["gold"] == 91 + 90 + 88


def test_not_enough_gold_or_resource_does_nothing_and_says_so():
    server, g = market_map(gold=149, food=99)
    assert market.order(g, "Steve", 1) == 0 and market.order(g, "Steve", 10) == 0
    assert (g.stock["gold"], g.stock["food"]) == (149, 99) and g.rates == market.RATES
    said = [c for c in server.log if c.startswith("tellraw Steve")]
    assert "Not enough gold." in said[0] and "Not enough food." in said[1]


def test_the_rates_stay_inside_the_aoe2_limits():
    server, g = market_map()
    g.rates = {"wood": 21, "food": 9998, "stone": 130}
    g.stock.update(wood=500, gold=10 ** 6)
    market.order(g, "Steve", 9, shift=True)
    market.order(g, "Steve", 1, shift=True)
    assert g.rates["wood"] == 20 and g.rates["food"] == 9999
    assert market.price(g, "wood", False) == 14 and market.price(g, "wood", True) == 26   # the wiki: 14/26
    assert market.price(g, "food", True) == 12999                       # the wiki: the highest buy price


def test_guilds_and_the_saracens_lower_the_fee():
    server, g = market_map()
    assert market.fee(g) == 30
    g.techs.add("GUILDS")
    assert market.fee(g) == 15 and market.price(g, "wood", False) == 85
    g.data["players"] = {"1": {"civ": "SARACENS"}}
    assert market.fee(g) == 5 and market.price(g, "wood", True) == 105


@pytest.mark.mc
def test_the_market_menu_items_are_good_on_paper(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import menu, run
    server, g = market_map()
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        assert game.command(menu.command("@a", "Market", market.items(g))).strip() == "Menu: 0 players"   # no "Bad item"
