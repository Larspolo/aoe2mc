"""
The AoE2 victory settings "Time Limit" and "Score" in the game program (#2356, epic #2263), from the score of score.py.
- "time-limit": at the end of the time (AoE2 years of wonder.YEAR game seconds) the player with the highest
  score and its allies win; players with the same highest score win together. A conquest still wins before the end
  (conquest.tick runs first in gather.Gather.run and ends the game).
- "score": the first player whose score reaches the target wins, with its allies.
Minecraft feature: a boss bar shows the years left, or the target score, to all players (as wonder.py). The end goes
through cheats.over, so the allies win together and cheats.over closes the bar.

    time_limit.tick(g, dt)   # gather.Gather.run: dt game seconds, after score.tick
"""
import json
import math

import cheats
import score
from wonder import YEAR

YEARS = 500          # the time limit when run.py --victory-value does not give one
POINTS = 10000       # the score target when run.py --victory-value does not give one
BAR = "aoe2mc:time_limit"


def close(g):
    """Remove the boss bar: the game ended (cheats.over)."""
    if vars(g).pop("limit_shown", None) is not None:
        g.command(f"bossbar remove {BAR}")


def show(g, name, value, top):
    """Show the boss bar with name and value of top; a command only when the value changes."""
    if vars(g).get("limit_shown") is None:
        for c in (f'bossbar add {BAR} ""', f"bossbar set {BAR} color purple", f"bossbar set {BAR} max {max(1, top)}",
                  f"bossbar set {BAR} players @a"):
            g.command(c)
    elif g.limit_shown == value:
        return
    g.limit_shown = value
    g.command(f"bossbar set {BAR} name " + json.dumps(name))
    g.command(f"bossbar set {BAR} value {max(0, min(value, top))}")


def best(g):
    """The highest score of the game of g and the players with it."""
    scores = {n: score.total(p) for n, p in score.points(g).items()}
    top = max(scores.values(), default=0)
    return top, [n for n, s in scores.items() if s == top]


def win(g, players):
    """End the game: players and their allies win."""
    from gather import allied  # gather imports this module
    cheats.over(g, lambda m: any(allied(g.players, n, m) for n in players))


def tick(g, dt):
    """Count down the time limit by dt game seconds, or check the score target, and end the game."""
    if g.ended:
        return
    value = getattr(g, "victory_value", None)
    if g.victory == "time-limit":
        total = (value or YEARS) * YEAR
        g.limit_left = vars(g).get("limit_left", total) - dt
        if g.limit_left <= 0:
            return win(g, best(g)[1])
        y = math.ceil(g.limit_left / YEAR)
        return show(g, f"Time limit: {y} year{'s' * (y != 1)} left", y, int(total / YEAR))
    if g.victory == "score" and g.clock() >= vars(g).get("limit_at", 0.0):
        g.limit_at = g.clock() + score.EVERY                        # not each tick: points() reads all Gathers
        target = value or POINTS
        top, players = best(g)
        if top >= target:
            return win(g, players)
        show(g, f"Score victory: {target} points", top, target)
