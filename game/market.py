"""
Buy and sell resources at an own market in the game program, as in AoE2 DE (#1252). A right click on an own complete
market opens its chest menu (menu.py): one buy and one sell item for wood, food and stone, with the present price in
gold. Each trade is 100 of the resource (a shift click: 5 trades, 500, as in AoE2). The price comes from the exchange
rate of the resource (RATES: gold per 100, global for all players in AoE2) and the trading fee of the player (FEE):
a buy costs rate × (1 + fee), a sell gives rate × (1 - fee). Each buy raises the rate by STEP, each sell lowers it,
inside LIMITS. Values: the AoE2 wiki, "Market (Age of Empires II)", section on the exchange.
gather.Gather.click calls open_menu().
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import civs  # noqa: E402
import menu  # noqa: E402
import table  # noqa: E402

RATES = {"wood": 100, "food": 115, "stone": 130}                   # the AoE2 DE start rates, gold per 100
STEP = 2                                                           # the rate change of one trade
LIMITS = (20, 9999)                                                # the lowest and the highest rate
LOT = 100                                                          # the resource of one trade
SHIFT = 5                                                          # trades of a shift click (500, as in AoE2)
FEE = 30                                                           # the commodity trading fee in percent
FEES = {r["name"]: r["fee"] for r in table.load("train.jsonl") if "fee" in r}   # a technology of the player: its fee
CIV_FEES = {"SARACENS": 5}                                         # the civilization bonus of the Saracens
ITEMS = {"wood": "oak_log", "food": "wheat", "stone": "cobblestone"}   # the menu item of each resource
SELL = 9                                                           # the first slot of the sell row
ROW = 18                                                           # the buy row in the menu of the market (train.show, #1286)


def rates(g):
    """The exchange rates of g (the start rates on the first call)."""
    if not hasattr(g, "rates"):
        g.rates = dict(RATES)
    return g.rates


def fee(g):
    """The trading fee of the player in percent: the lowest of FEE, its technologies and its civilization."""
    return min([FEE, CIV_FEES.get(civs.civ(g), FEE)] + [f for t, f in FEES.items() if t in getattr(g, "techs", ())])


def price(g, resource, buy):
    """The gold of one trade of 100 resource: the cost of a buy, or the gain of a sell. Rounded half up, as the wiki
    numbers (0.7 × 115 = 80.5 gives 81)."""
    f = 100 + fee(g) if buy else 100 - fee(g)
    return (rates(g)[resource] * f + 50) // 100


def markets(g):
    """The block footprints (x0, x1, z0, z1) of the complete own markets: the start ones and the built ones."""
    out = [(x0, x1, z0, z1) for o in g.data["objects"] if o["kind"] == "building" and o["name"] == "MARKET"
           and o["player"] == g.player for x0, z0, x1, z1 in [o["footprint"]]]
    return out + [tuple(s["footprint"]) for s in g.sites if s["name"] == "MARKET" and s.get("done")
                  and s.get("player", g.player) == g.player]


def home(g, cell):
    """The footprint of the own market that has the block cell (x, z) in it, or None."""
    return next((r for r in markets(g) if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)


def open_menu(g, player, cell):
    """Open the menu of the own market at the block cell (x, z) for player. Returns its footprint, or None."""
    rect = home(g, cell)
    if rect is not None:
        show(g, player)
    return rect


def items(g):
    """The menu items: the buy row first, then the sell row, in the order of RATES."""
    return [(i, ITEMS[r], f"Buy {LOT} {r}", f"{price(g, r, True)} gold") for i, r in enumerate(RATES)] + \
        [(SELL + i, ITEMS[r], f"Sell {LOT} {r}", f"{price(g, r, False)} gold") for i, r in enumerate(RATES)]


def show(g, player):
    menu.show(g, player, build.pretty("MARKET"), items(g), lambda p, slot, shift: order(g, p, slot, shift))


def add(g, resource, n):
    g.stock[resource] += n
    g.command(f"scoreboard players {'add' if n > 0 else 'remove'} {resource.capitalize()} {g.board} {abs(n)}")


def trade(g, player, resource, buy):
    """One trade of 100 resource for gold. Returns True, or False and the AoE2 message when the player has not enough
    gold (a buy) or resource (a sell)."""
    gold = price(g, resource, buy)
    if buy and g.stock["gold"] < gold or not buy and g.stock[resource] < LOT:
        build.say(g, player, f"Not enough {'gold' if buy else resource}.")
        return False
    add(g, "gold", -gold if buy else gold)
    add(g, resource, LOT if buy else -LOT)
    r = rates(g)
    r[resource] = min(max(r[resource] + (STEP if buy else -STEP), LIMITS[0]), LIMITS[1])
    return True


def order(g, player, slot, shift=False, refresh=None):
    """A click on the menu item in slot: 1 trade (a shift click: SHIFT, while the stock allows), then refresh the
    menu with the new prices (refresh(), else show()). Returns the number of trades."""
    names, buy = list(RATES), slot < SELL
    i = slot if buy else slot - SELL
    n = 0
    while 0 <= i < len(names) and n < (SHIFT if shift else 1) and trade(g, player, names[i], buy):
        n += 1
    (refresh or (lambda: show(g, player)))()
    return n
