"""
The AoE2 relic victory in the game program (#1263, epic #1134): a player whose own monasteries hold all relics of the
map for the relic timer wins, as in the AoE2 DE "Standard" game. The timer has the length of the wonder timer
(wonder.years: AoE2 wiki, "Wonder (Age of Empires II)", section WonderRelicVictoryTime, which the page "Relic (Age of
Empires II)" includes). A relic that leaves a monastery (the monastery falls, monk.relic_tick) stops the timer, and a
new holder starts it again from the full time. With no relic on the map there is no relic victory.
All Gathers of a game share one list of the relics (monk.relics, #3116): a player holds a relic when it is in a
monastery of its Gather (the people and each bot; bot.Bot holds its Gather in b.g). The boss bar aoe2mc:relics shows
the countdown to all players (Minecraft feature, as wonder.py), and gather.Gather.run gives tick() the game seconds
(tick × NORMAL). At the end, the human player sees "Victory" for its own relics and "Defeat" for the relics of a
rival; the game then ends (g.ended), and cheats.end calls close().
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cheats  # noqa: E402
import lang  # noqa: E402
import monk  # noqa: E402
import wonder  # noqa: E402

BAR = "aoe2mc:relics"


def holder(g):
    """The player whose own monasteries hold all relics of the map, else None."""
    for b in [g, *(b.g for b in getattr(g, "bots", ()))]:            # a bot.Bot: its Gather
        rs, homes = monk.relics(b), monk.monasteries(b)
        if rs and all(r["home"] in homes for r in rs):
            return b.player
    return None


def close(g):
    """Remove the boss bar: the game ended (cheats.end), no countdown goes on."""
    if vars(g).pop("relic_timer", None):
        g.command(f"bossbar remove {BAR}")


def tick(g, dt):
    """Start, count down by dt game seconds, or stop the relic timer, and end the game at 0."""
    if g.ended:
        return
    t, n = vars(g).get("relic_timer"), holder(g)
    if t and t["player"] != n:                                       # a relic left the monasteries of the holder
        close(g)
        g.command("tellraw @a " + json.dumps(lang.text("aoe2mc.relic_victory.lost", t["player"], color="red")))
        t = None
    if n is None:
        return
    if not t:
        total = wonder.years(g.data.get("map_size")) * wonder.YEAR
        g.relic_timer = t = {"player": n, "left": total, "shown": None}
        for c in (f'bossbar add {BAR} ""', f"bossbar set {BAR} color purple", f"bossbar set {BAR} max {int(total / wonder.YEAR)}",
                  f"bossbar set {BAR} players @a"):
            g.command(c)
        g.command("tellraw @a " + json.dumps(lang.text("aoe2mc.relic_victory.all", n, color="yellow")))
    if (more := wonder.later(g, t)) is not None:                    # an enemy researched Atheism (#4336)
        g.command(f"bossbar set {BAR} max {int((wonder.years(g.data.get('map_size')) * wonder.YEAR + more) / wonder.YEAR)}")
    t["left"] -= dt
    if t["left"] <= 0:
        from gather import allied  # gather imports this module
        return cheats.over(g, lambda m: allied(g.players, n, m))   # n and its allies win (#1936)
    if (y := math.ceil(t["left"] / wonder.YEAR)) != t["shown"]:       # a command only when the years change
        t["shown"] = y
        g.command(f"bossbar set {BAR} name " + json.dumps(f"Player {n}: relics, {y} year{'s' * (y != 1)} left"))
        g.command(f"bossbar set {BAR} value {y}")
