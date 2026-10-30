"""
The AoE2 DE lobby setting "Treaty length" in the game program (#2297, epic #2263): until the end of the treaty, no
player can attack another player. run.py --treaty MM:SS calls start(). An attack order on a unit or building of another
player (gather.Gather.click) then does nothing, and the player sees a chat line (refuse). The bot waits too: run.py gives
it the later of --bot-attack and the treaty as its attack time.
Minecraft feature: the plugin command `aoe neutral` (gather.neutral_command, #1645) stops the automatic attacks of the
units and buildings (towers, town centers) on a neutral player. During the treaty each player is neutral to all others;
at the end the neutral stances of aoe2mc.json come back. The scoreboard teams (friendly fire) are not used: a team is
one player or one alliance (gather.allies_command), so one team for all would make all players allies.
The program counts game time: tick() adds dt (game seconds) at each call, gather.Gather.run gives it tick × NORMAL,
as for the wonder timer. The state is on the Game, so all Gathers (people, bots) share it.
A game mode with the key "treaty": "endless" in game/data/setup.jsonl (Wonder Race, #2406) has a treaty with no end:
start(g, math.inf).
Minecraft feature: a boss bar "Treaty: M:SS left" for all players (#2962), as time_limit.py. Its value is the seconds left.
A treaty with no end has no bar. cheats.over removes it when the game ends.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table  # noqa: E402

ENDLESS = {r["name"] for r in table.load("setup.jsonl") if r.get("treaty") == "endless"}   # the modes with no attacks
BAR = "aoe2mc:treaty"


def clock(seconds):
    """MM:SS of game seconds."""
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def until(seconds):
    """The end of a treaty of seconds in a chat line: "before MM:SS", or "in this game" for a treaty with no end."""
    return "in this game" if math.isinf(seconds) else f"before {clock(seconds)}"


def truce_command(players):
    """The plugin command that makes each player neutral to all others: "aoe neutral p1:p2,p3 p2:p1,p3 p3:p1,p2"."""
    ns = sorted(players)
    return "aoe neutral " + " ".join(f"p{n}:" + ",".join(f"p{m}" for m in ns if m != n) for n in ns)


def start(g, seconds, done=0.0):
    """Start a treaty of seconds (game time) for the Gather g and all Gathers that share its game. 0: no treaty,
    math.inf: a treaty with no end (ENDLESS). done: the game seconds of the treaty that passed before the save of a
    loaded game (savegame "treaty_time", #2409); a treaty that ended before the save does not start again."""
    g.game.treaty, g.game.treaty_time = seconds, done
    if seconds > done and g.paper:
        g.command(truce_command({int(n) for n in g.data.get("players", {})} | {g.player}))
    if seconds > done:
        g.command("tellraw @a " + json.dumps({"text": f"Treaty: no player can attack another player "
                                                      f"{until(seconds)}.", "color": "yellow"}))
    show(g)


def show(g):
    """The boss bar of the treaty: the seconds left as its value, a command only when the whole second changes.
    A treaty with no end (math.inf) has no bar."""
    game = g.game
    if math.isinf(game.treaty) or game.treaty_time >= game.treaty:
        return
    left = math.ceil(game.treaty - game.treaty_time)
    if vars(game).get("treaty_bar") == left:
        return
    if vars(game).get("treaty_bar") is None:
        for c in (f'bossbar add {BAR} ""', f"bossbar set {BAR} color yellow",
                  f"bossbar set {BAR} max {math.ceil(game.treaty)}", f"bossbar set {BAR} players @a"):
            g.command(c)
    game.treaty_bar = left
    g.command(f"bossbar set {BAR} name " + json.dumps(f"Treaty: {clock(left)} left"))
    g.command(f"bossbar set {BAR} value {left}")


def close(g):
    """Remove the boss bar: the game ended (cheats.over), or the treaty ended."""
    game = getattr(g, "game", None)                                    # a test Gather can have none
    if game is not None and vars(game).pop("treaty_bar", None) is not None:
        g.command(f"bossbar remove {BAR}")


def holds(g):
    """True while the treaty of the game of g goes on."""
    game = getattr(g, "game", None)                                    # a test Gather can have none
    return getattr(game, "treaty_time", 0.0) < getattr(game, "treaty", 0.0)


def refuse(g, name):
    """True when the treaty stops an attack order of player name: then name sees a chat line."""
    if not holds(g):
        return False
    g.command(f"tellraw {name} " + json.dumps({"text": f"Treaty: you cannot attack {until(g.game.treaty)}.",
                                               "color": "red"}))
    return True


def tick(g, dt):
    """Count dt game seconds; at the end of the treaty tell all players and give back the neutral stances."""
    if not holds(g):
        return
    g.game.treaty_time += dt
    if holds(g):
        return show(g)
    close(g)
    import gather  # gather imports this module
    if g.paper:
        g.command(gather.neutral_command(g.data.get("players", {})))
    g.command("tellraw @a " + json.dumps({"text": "The treaty ended: players can attack now.", "color": "yellow"}))
