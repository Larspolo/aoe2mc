"""
The Game menu and its Diplomacy page in the game program (#1588, owner decision #1314: option B). A hotbar item (ITEM,
in hotbar slot SLOT) stands for the buttons at the top right of the AoE2 DE screen: a right click opens the Game menu
(menu.py), and its first button is "Diplomacy". The Diplomacy page has one column for each other player of aoe2mc.json:
the wool of its color with its name on top, then one item for each resource. A click sends a tribute of LOT of the
resource to that player (a shift click: SHIFT × LOT, as market.SHIFT).
AoE2 rules (AoE2 wiki, "Tribute"): the sender pays a fee of FEE % on top (100 food to send costs 130 food), and the
receiver gets the full amount. A player needs a complete own market to send tribute. Coinage (20 %) and Banking (0 %)
of the sender lower the fee (FEES, #1606).
The receiver is the Gather of that player (the human player or a bot of g.bots). A player without a Gather (no program
plays it) keeps its tribute in g.tributes.
gather.Gather.clicks gives the item and opens the menu.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mc import player_color  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import flare  # noqa: E402
import lobby  # noqa: E402
import market  # noqa: E402
import menu  # noqa: E402
import savegame  # noqa: E402
import table  # noqa: E402

SLOT = 3                                                           # hotbar slot of the item (key 4): groups use 4-8
ITEM = ('minecraft:carrot_on_a_stick[item_model="minecraft:writable_book",item_name="Game menu",'
        "custom_data={aoe_game_menu:1b}]")
BUTTONS = {0: ("writable_book", "Diplomacy", "Send tribute to other players."),   # slot: the buttons of the Game menu
           1: ("end_rod", "Flare", "Show the place that you look at to your team."),   # (#1234)
           3: ("writable_book", "Save", "Save the game. Load it with run.py --load.")}     # savegame.py (#2259)
SPEED_SLOT = 4                                                     # the button "Game speed" with --unlock-speed (#2933)
SPEEDS = (1.0, 1.5, 2.0)                                           # times the Normal speed, as run.py --speed
RESOURCES = {"food": "wheat", "wood": "oak_log", "gold": "gold_ingot", "stone": "cobblestone"}   # rows 1-4
LOT = 100                                                          # the resource of one click
SHIFT = 5                                                          # tributes of a shift click (500)
FEE = 30                                                           # the tribute fee in percent, paid by the sender
# A technology of the sender: its fee (#1606, the key "tribute_fee" of data/train.jsonl)
FEES = {r["name"]: r["tribute_fee"] for r in table.load("train.jsonl") if "tribute_fee" in r}


def give(g):
    """Put the item into hotbar slot SLOT of each player that has no Game menu item there."""
    g.command(f"execute as {g.who} unless items entity @s hotbar.{SLOT} *[custom_data={{aoe_game_menu:1b}}] "
              f"run item replace entity @s hotbar.{SLOT} with {ITEM}")


def in_hand(g, player):
    """True when player holds the Game menu item in the main hand."""
    return "passed" in g.command(f"execute if items entity {player} weapon.mainhand *[custom_data={{aoe_game_menu:1b}}]")


def open_menu(g, player):
    """The Game menu: one item for each button; "Choose your player" in a game of more people (lobby.py, #1563)."""
    buttons = BUTTONS | ({lobby.SLOT: lobby.BUTTON} if lobby.shown(g) else {}) | \
        ({SPEED_SLOT: ("clock", "Game speed", f"Now {main(g).speed:g}. Click: {after(main(g).speed):g}.")}
         if getattr(g, "unlock_speed", False) else {})   # AoE2 "Lock Speed" off (#2933)
    menu.show(g, player, "Game menu", [(s, m, n, lore) for s, (m, n, lore) in buttons.items()],
              lambda p, slot, shift: button(g, p, slot))


def button(g, player, slot):
    """A click on the Game menu: the Diplomacy page, a flare at the look of the player (the menu closes, #1234), a
    save of the game (#2259), or the next game speed (#2933)."""
    if slot == 0:
        return show(g, player)
    if slot == 1:
        menu.close(g, player)
        return flare.from_look(g, player)
    if slot == 3:
        menu.close(g, player)
        return savegame.save(g, player)
    if slot == lobby.SLOT and lobby.shown(g):
        return lobby.show(g, player)
    if slot == SPEED_SLOT and getattr(g, "unlock_speed", False):
        menu.close(g, player)
        return faster(g)


def main(g):
    """The Gather of player 1 that runs the game (run.play: game.g), else g."""
    return getattr(g.game, "g", None) or g


def after(speed):
    """The next speed of SPEEDS; after the last one the first."""
    return next((s for s in SPEEDS if s > speed), SPEEDS[0])


def faster(g):
    """The next game speed for all players (AoE2 "Lock Speed" off, #2933), as run.py --speed: the server ticks faster
    and the steps of the Gathers are shorter. t0 moves, so that the game time of recap.game_time does not jump."""
    import run
    x = main(g)
    old, new = x.speed, after(x.speed)
    now = x.clock()
    for h in [x, *(b.g for b in x.bots)]:
        h.speed = new
        h.t0 = now - (now - h.t0) * old / new
    g.command(f"tick rate {run.TICKS * new:g}")
    g.command("tellraw @a " + json.dumps({"text": f"Player {g.player} set the game speed to {new:g}.",
                                          "color": "gold"}))
    return new


def others(g):
    """The other players of aoe2mc.json (not Gaia), in number order."""
    return sorted(int(n) for n in g.players if int(n) not in (0, g.player))[:9]


def name(g, n):
    civ = getattr(g, "trigger_civs", {}).get(str(n)) or build.pretty(g.players[str(n)].get("civ") or "")
    return f"Player {n}" + (f" ({civ})" if civ else "")              # a scenario trigger renames it (#2905)


def items(g):
    """The Diplomacy page: column i is player others(g)[i], row 0 its wool, rows 1-4 its resources."""
    out = []
    for i, n in enumerate(others(g)):
        color = g.players[str(n)].get("color") or player_color(n)
        out.append((i, f"{color}_wool", name(g, n), ""))
        out += [(9 * (r + 1) + i, m, f"Send {LOT} {res}", f"{cost(g, LOT)} {res} with the fee")
                for r, (res, m) in enumerate(RESOURCES.items())]
    return out


def show(g, player):
    menu.show(g, player, "Diplomacy", items(g), lambda p, slot, shift: order(g, p, slot, shift))


def fee(g):
    """The tribute fee of the player g in percent: the lowest of FEE and its technologies."""
    return min([FEE] + [f for t, f in FEES.items() if t in getattr(g, "techs", ())])


def cost(g, n):
    """What the sender g pays for a tribute of n: n and the fee."""
    return n * (100 + fee(g)) // 100


def receiver(g, n):
    """The Gather of player n (g itself or a bot), or None."""
    return next((x for x in [g] + [b.g for b in g.bots] if x.player == n), None)


def send(g, player, n, res):
    """One tribute of LOT res to player n. Returns True, or False and the AoE2 message."""
    if not market.markets(g):
        build.say(g, player, "Build a market to send tribute.")
        return False
    if g.stock[res] < cost(g, LOT):
        build.say(g, player, f"Not enough {res}.")
        return False
    market.add(g, res, -cost(g, LOT))
    if (r := receiver(g, n)) is not None:
        market.add(r, res, LOT)
    else:
        tributes = vars(g).setdefault("tributes", {})
        tributes.setdefault(n, dict.fromkeys(RESOURCES, 0))[res] += LOT
    g.command("tellraw @a " + json.dumps({"text": f"Player {g.player} sent {LOT} {res} to player {n}.",
                                          "color": "gold"}))
    return True


def order(g, player, slot, shift=False):
    """A click on the Diplomacy page: the resource item in column i sends tribute to player others(g)[i] (a shift
    click: SHIFT tributes, while the stock allows). Returns the number of tributes."""
    col, row, players = slot % 9, slot // 9, others(g)
    k = 0
    while 1 <= row <= len(RESOURCES) and col < len(players) and k < (SHIFT if shift else 1) \
            and send(g, player, players[col], list(RESOURCES)[row - 1]):
        k += 1
    return k
