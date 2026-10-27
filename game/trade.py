"""
The trade carts of the game program (#1253, epic #1250). The market trains a trade cart (train.TRAINS). A right click
with selected trade carts on a second own market sends them on a trade route: each cart walks to the door of that
market, back to the door of its home market (the nearest other own market), and each arrival at home adds the gold of
the AoE2 formula (GOLD) to the stock of the player. Then it walks again, until the player gives another order.

AoE2 DE trades only with the markets of other players; the game program has no allies yet (roadmap `play:diplomacy`),
so a cart trades between two own markets here, with the same formula.

Gold per trip (AoE2 wiki, "Market (Age of Empires II)", trading): 0.46 * d * (d / map size + 0.3), with d the distance
in tiles between the market centers less 5 tiles on each axis, at least 0.1. The cart keeps the fraction for its next
trip, as in AoE2 (fractional gold).

Minecraft feature: the walk is the path finding of the Paper plugin (`aoe moveto`, ai.py) at the AoE2 speed.

    trade.order(g, player, cell)   # gather.Gather.click: a right click on an own market
    trade.tick(g)                  # gather.Gather.step: the arrivals
"""
import math

GOLD = (0.46, 0.3)      # the factors of the AoE2 formula
FREE = 5                # tiles of each axis that give no gold
ARRIVE = 1.5            # blocks from the door cell: the cart is there
CART = "TRADE_CART"


def gold(a, b, size):
    """The gold of one trip between the markets with the centers a and b (tiles) on a map of size tiles."""
    d = max(0.1, math.hypot(*(max(0.0, abs(p - q) - FREE) for p, q in zip(a, b))))
    return GOLD[0] * d * (d / size + GOLD[1])


def center(rect, T):
    """The center (x, z) in tiles of the block footprint rect (x0, x1, z0, z1)."""
    return (rect[0] + rect[1]) / 2 / T, (rect[2] + rect[3]) / 2 / T


def markets(g):
    """The block footprints of the complete own markets."""
    import train                                                   # train imports gather, gather imports this module
    return sorted(r for r, n in train.homes(g).items() if n == "MARKET")


def walk(g, uuid, rect):
    """Send cart uuid to the door cell of the market rect. Returns the cell, or None."""
    import ai, train                                               # both import gather, gather imports this module
    if not (to := next(iter(g.map.front(rect)), None)):
        return None
    x, z = to
    ai.move(g, uuid, CART, g.map.T, x + 0.5, g.map.y(x, z), z + 0.5, ai.NORMAL * train.speed(g, CART))
    return to


def order(g, player, cell):
    """The selected trade carts trade with the own market with the block cell (x, z) in its footprint. Returns its
    footprint, or None (no own market there, no cart selected, no second own market or no plugin): the click is then
    not a trade order."""
    own = markets(g)
    rect = next((r for r in own if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)
    carts = sorted(u for u in g.selected if g.soldiers.get(u, "").startswith(CART))   # also TRADE_CART_FULL
    if rect is None or not carts or len(own) < 2 or not g.paper:
        return None
    pos = g.positions(carts)
    for u in carts:
        if u not in pos:
            continue
        mid = lambda r: ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2)    # noqa: E731
        home = min((r for r in own if r != rect), key=lambda r: (math.dist(mid(r), (pos[u][0], pos[u][2])), r))
        if (to := walk(g, u, rect)) is not None:
            g.trade[u] = {"home": home, "market": rect, "to": rect, "cell": to, "rest": g.trade.get(u, {}).get("rest", 0.0)}
    g.mark(player, {(rect[0], rect[2]), (rect[1] - 1, rect[3] - 1)})
    return rect


def tick(g):
    """Turn each cart at its target: at the far market it walks home, at home it gives its gold and walks out again."""
    if not g.trade:
        return
    own = set(markets(g))
    pos = g.positions(sorted(g.trade))
    for u, t in sorted(g.trade.items()):
        if u not in pos or not g.soldiers.get(u, "").startswith(CART) or not {t["home"], t["market"]} <= own:
            del g.trade[u]                                         # dead, or a market fell: the route ends
            continue
        x, z = t["cell"]
        if math.dist((pos[u][0], pos[u][2]), (x + 0.5, z + 0.5)) > ARRIVE:
            continue
        if t["to"] == t["home"]:
            t["rest"] += gold(center(t["home"], g.map.T), center(t["market"], g.map.T), g.map.n / g.map.T)
            n, t["rest"] = int(t["rest"]), t["rest"] - int(t["rest"])
            if n:
                g.command(f"scoreboard players add Gold {g.board} {n}")
                g.stock["gold"] += n
        t["to"] = t["market"] if t["to"] == t["home"] else t["home"]
        t["cell"] = walk(g, u, t["to"]) or t["cell"]
