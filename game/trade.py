"""
The trade carts of the game program (#1253, epic #1250). The market trains a trade cart (train.TRAINS). A right click
with selected trade carts on a second own market sends them on a trade route: each cart walks to the door of that
market, back to the door of its home market (the nearest other own market), and each arrival at home adds the gold of
the AoE2 formula (GOLD) to the stock of the player. Then it walks again, until the player gives another order.

AoE2 DE trades only with the markets of other players; the game program has no allies yet (roadmap `play:diplomacy`),
so a cart trades between two own markets here, with the same formula.

The Caravanserai of the Hindustanis and Persians (Imperial Age, #2341) makes the trade carts of its player and its
allies 20 % faster in its aura (AURAS, AoE2 wiki "Caravanserai (Age of Empires II)"), and it heals them there by 1 hit
point per AoE2 second (HEALS, #2353), with the Health change of monk.heal once each HEAL_EVERY AoE2 seconds.

Gold per trip (AoE2 wiki, "Market (Age of Empires II)", trading): 0.46 * d * (d / map size + 0.3), with d the distance
in tiles between the market centers less 5 tiles on each axis, at least 0.1. The cart keeps the fraction for its next
trip, as in AoE2 (fractional gold).

Minecraft feature: the walk is the path finding of the Paper plugin (`aoe moveto`, ai.py) at the AoE2 speed. One
Minecraft path search reaches only about 128 blocks, so a long way goes in legs of LEG cells of the path of gather.Map,
as in the live replay (#438, #1305: a cart turned back after 125 of 170 blocks).

    trade.order(g, player, cell)   # gather.Gather.click: a right click on an own market
    trade.tick(g)                  # gather.Gather.step: the arrivals
    trade.heal(g, dt)              # gather.Gather.step: dt AoE2 seconds of the heal in the auras
"""
import math

import table

GOLD = (0.46, 0.3)      # the factors of the AoE2 formula
FREE = 5                # tiles of each axis that give no gold
ARRIVE = 1.5            # blocks from the door cell: the cart is there
LEG = 48                # path cells of one plugin order: within the reach of a Minecraft path search (replay.LEG)
NEAR = 3                # blocks from the end of a leg: the next leg starts
PATH_CELLS = 20000      # cells that one path search may look at (replay.PATH_CELLS)
CART = "TRADE_CART"
# The buildings that speed up the trade carts of their player and its allies (#2341): {name: (speed factor, tiles of
# the aura from each edge)}; the aura is a square, as in AoE2 (the Caravanserai: +20 %, 8 tiles).
AURAS = {r["name"]: (r["cart_speed"], r["aura"]) for r in table.load("buildings.jsonl") if "cart_speed" in r}
# The buildings that heal them in the same aura (#2353): {name: (hit points per AoE2 second, tiles)}.
HEALS = {r["name"]: (r["cart_heal"], r["aura"]) for r in table.load("buildings.jsonl") if "cart_heal" in r}
HEAL_EVERY = 5.0        # AoE2 seconds between two heal passes (fewer commands, garrison.HEAL_EVERY)


GOLD_RATES = {r["name"]: r["gold_rate"] for r in table.load("train.jsonl") if "gold_rate" in r}   # trade, relics


def gold_rate(g):
    """The factor of the trade and relic gold of the player g: the product of its technologies (GOLD_RATES)."""
    return math.prod(GOLD_RATES.get(t, 1) for t in getattr(g, "techs", ()))


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


def walk(g, uuid, rect, pos):
    """Send cart uuid at block position pos to the door cell of the market rect, in legs of LEG cells of the path.
    Returns the end cells of the legs (the door last; the cart walks to the first one now), or None."""
    if not (to := next(iter(g.map.front(rect)), None)):
        return None
    path = g.map.path((int(pos[0]), int(pos[2])), {to}, PATH_CELLS)
    legs = (path[LEG - 1:-1:LEG] if path else []) + [to]
    leg(g, uuid, legs[0])
    return legs


def covers(g, cell, auras):
    """The values of auras ({name: (value, tiles of the aura from each edge)}) of the complete buildings of the player
    and its allies (gather.allied) with the block cell (x, z) in their aura."""
    import gather                                                  # gather imports this module
    start = [(o["player"], o["name"], (x0, x1, z0, z1)) for o in g.data["objects"] if o["kind"] == "building"
             and o["name"] in auras for x0, z0, x1, z1 in [o["footprint"]]]
    built = [(s["player"], s["name"], tuple(s["footprint"])) for s in g.sites if s["name"] in auras and s.get("done")]
    x, z = cell
    return [auras[n][0] for p, n, (x0, x1, z0, z1) in start + built if gather.allied(g.players, g.player, p)
            and x0 - (r := auras[n][1] * g.map.T) <= x < x1 + r and z0 - r <= z < z1 + r]


def aura(g, cell):
    """The speed factor of a trade cart of the player at the block cell (x, z): the largest one of AURAS of the complete
    buildings of the player and its allies with the cell in their aura, else 1."""
    return max(covers(g, cell, AURAS), default=1.0)


def heal(g, dt):
    """Give the injured own trade carts in the aura of a building of HEALS their hit points back for dt AoE2 seconds
    (the Caravanserai: 1 per second, #2353), up to their max."""
    carts = sorted(u for u, n in g.soldiers.items() if n.startswith(CART))
    g.cart_heal = vars(g).get("cart_heal", 0.0) + dt if carts and HEALS else 0.0
    if g.cart_heal < HEAL_EVERY:
        return
    import monk                                                    # monk imports gather, gather imports this module
    dt, g.cart_heal = g.cart_heal, 0.0
    for u, (x, _, z) in sorted(g.positions(carts).items()):
        if (rate := max(covers(g, (math.floor(x), math.floor(z)), HEALS), default=0)) and (h := monk.health(g, u)) \
                and h[0] < h[1]:
            g.command(f"data modify entity {u} Health set value {round(min(h[1], h[0] + rate * dt), 2)}f")


def leg(g, uuid, cell):
    """The plugin walks cart uuid to the block cell (x, z) at the AoE2 speed of a trade cart (Caravan: train.speed),
    faster when the cell is in the aura of a Caravanserai (aura): the end cell of a leg gives the speed of the leg."""
    import ai, train                                               # both import gather, gather imports this module
    x, z = cell
    ai.move(g, uuid, CART, g.map.T, x + 0.5, g.map.y(x, z), z + 0.5, ai.NORMAL * train.speed(g, CART, uuid) * aura(g, cell))


def order(g, player, cell):
    """The selected trade carts trade with the own market with the block cell (x, z) in its footprint. Returns its
    footprint, or None (no own market there, no cart selected, no second own market or no plugin): the click is then
    not a trade order."""
    own = markets(g)
    rect = next((r for r in own if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)
    carts = sorted(u for u in g.selected if g.soldiers.get(u, "").startswith(CART))   # also TRADE_CART_FULL
    if rect is None or not carts or len(own) < 2 or not g.paper:
        return None
    rest = {u: g.trade[u].get("rest", 0.0) for u in carts if u in g.trade}   # new_order ends the old route
    g.new_order(carts)
    pos = g.positions(carts)
    for u in carts:
        if u not in pos:
            continue
        mid = lambda r: ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2)    # noqa: E731
        home = min((r for r in own if r != rect), key=lambda r: (math.dist(mid(r), (pos[u][0], pos[u][2])), r))
        if (legs := walk(g, u, rect, pos[u])) is not None:
            g.trade[u] = {"home": home, "market": rect, "to": rect, "cell": legs[-1], "legs": legs,
                          "rest": rest.get(u, 0.0)}
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
        if len(legs := t.get("legs") or []) > 1:                   # on a long way: the next leg at the end of one
            x, z = legs[0]
            if math.dist((pos[u][0], pos[u][2]), (x + 0.5, z + 0.5)) <= NEAR:
                legs.pop(0)
                leg(g, u, legs[0])
            continue
        x, z = t["cell"]
        if math.dist((pos[u][0], pos[u][2]), (x + 0.5, z + 0.5)) > ARRIVE:
            continue
        if t["to"] == t["home"]:
            import civs                                               # civs imports monk, which imports this module
            t["rest"] += gold(center(t["home"], g.map.T), center(t["market"], g.map.T), g.map.n / g.map.T) * gold_rate(g) \
                * civs.value("trade_gold", civs.civ(g), 1)            # Palmyrans +20 % (#4446); the relics do not get it
            n, t["rest"] = int(t["rest"]), t["rest"] - int(t["rest"])
            if n:
                g.earn("gold", n)
        t["to"] = t["market"] if t["to"] == t["home"] else t["home"]
        if (legs := walk(g, u, t["to"], pos[u])) is None:          # no free door at the next market: the route ends
            del g.trade[u]
        else:
            t["cell"], t["legs"] = legs[-1], legs
