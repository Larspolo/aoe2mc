"""A bot plays for a person who left a network game until the person joins again (#5893), as AoE2 DE does for a
dropped player: its villagers gather, its town defends; the join gives the same player back (team, units, stock).

The log thread of run.Game reads the leave and the join (Game.op_joined) and puts them into Game.drops. Only the
game loop (Gather.run calls tick) changes the stand-ins: one thread changes them. A stand-in is a bot.Bot over the
Gather of the person (own, as tools/play_check.py Driver): that Gather keeps its units and its stock. It is not in
Gather.bots: each entry there is the Gather of one player (herd, gaia, fog, savegame), and a second entry of the same
Gather does its work twice and saves the person as a bot."""
import json
import math

import lang

LEFT_KEY = "aoe2mc.run.left_bot"                     # "<name> left: a bot plays player N"
BACK_KEY = "aoe2mc.run.back"                         # "<name> is back"


def tick(g):
    """Do the leave and join events of the log (Game.drops) in this order, then give the orders of each stand-in."""
    drops = getattr(getattr(g, "game", None), "drops", None)
    while drops:
        event, name = drops.popleft()
        (leave if event == "left" else back)(g, name)
    for b in vars(g).get("stand_ins", {}).values():
        b.orders()                                    # the Gather of the person steps itself (g.run, run.Side)


def gathers(g):
    """AoE2 player -> its Gather: g and the Gathers of g.bots (the people and the bots)."""
    return {x.player: x for x in [*(getattr(b, "g", None) for b in reversed(getattr(g, "bots", ()))), g] if x is not None}


def leave(g, name):
    """Person name left after the start: a bot plays its AoE2 player, when no other person of that player (co-op,
    --seats) is online and no bot plays it yet."""
    import bot
    import run
    game = g.game
    n = game.sides.get(name)
    if not n or any(k == n and p in game.joined for p, k in game.sides.items() if p != name):
        return
    stand_ins, sides = vars(g).setdefault("stand_ins", {}), gathers(g)
    x = sides.get(n)
    if x is None or n in stand_ins or any(getattr(b, "own", False) and b.g is x for b in getattr(g, "bots", ())):
        return
    foe = run.bot_foe(x.data["players"], n)
    kept = x.chop                                                      # Bot changes it by the difficulty
    b = bot.Bot(game, x.data, player=n, share=sides.get(foe, g), attack=math.inf, foe=foe, own=x)
    b.kept, b.scouted = kept, True                                     # the scouts stay where the person left them
    stand_ins[n] = b
    tell(g, LEFT_KEY, name, n)


def back(g, name):
    """Person name joined again: the bot of its AoE2 player stops, and the person has the Gather as the bot left it."""
    n = g.game.sides.get(name)
    b = vars(g).get("stand_ins", {}).pop(n, None)
    if b is None:
        return
    x = b.g
    x.chop = b.kept
    for k in ("home", "work_on"):                                      # Bot set them: the Gather values again
        vars(x).pop(k, None)
    tell(g, BACK_KEY, name)


def tell(g, key, *args):
    g.game.command("tellraw @a " + json.dumps(lang.text(key, *args, color="yellow")))
