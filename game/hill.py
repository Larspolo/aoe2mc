"""
The AoE2 victory "King of the Hill" in the game program (#2360, epic #2263): `game/run.py --victory king-of-the-hill`.
The player who holds the monument in the center of the map for 550 years wins, with its allies (AoE2 wiki, "King of the
Hill" and "Monument (Age of Empires II)"). The monument is the MONUMENT of aoe2mc.json, else the center of the map.
The owner keeps the monument while one of its units is within REACH tiles of it. When no unit of the owner is there,
the player of the nearest unit there captures it (the first player on equal distance). The timer counts down only while
a player holds the monument and goes on for the new owner, but a capture by a player who is not allied with the owner
sets a timer below RESET years back to RESET years.
The boss bar aoe2mc:hill shows the countdown to all players (Minecraft feature, as relic_victory.py), and
gather.Gather.run gives tick() the game seconds. At the end, cheats.over gives "Victory" to the owner and its allies.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cheats  # noqa: E402
import wonder  # noqa: E402

BAR = "aoe2mc:hill"
YEARS = 550             # years of the timer (AoE2 wiki, "Monument")
RESET = 100             # years: a capture by a player who is not allied sets a shorter timer back to this
REACH = 6               # tiles from the center of the monument (5 × 5 tiles): the wiki gives no number for its area
EVERY = 2.0             # game seconds between two checks of the unit positions


def center(g):
    """(x, z) in tiles of the monument: the first MONUMENT of aoe2mc.json, else the center of the map."""
    m = next((o["tile"] for o in g.data["objects"] if o["name"] == "MONUMENT"), None)
    n = g.data.get("map_size") or g.map.n / g.map.T
    return tuple(m) if m else (n / 2, n / 2)


def units(g):
    """{uuid: player} of the units of the players: those of aoe2mc.json, and those of each Gather of the game (fog.gathers:
    its own units, the bots, the peers)."""
    import fog                                                     # fog imports gather, gather imports this module
    out = {o["uuid"]: o["player"] for o in g.data["objects"] if o["kind"] == "unit" and o.get("uuid") and o["player"]}
    for h in fog.gathers(g):
        out.update(dict.fromkeys([*h.villagers, *h.soldiers], h.player))
    return out


def owner(g, now):
    """The player who holds the monument after a check: now, while a unit of now is within REACH, else the player of the
    nearest unit there (the first player on equal distance), else now."""
    who = units(g)
    cx, cz = center(g)
    near = sorted((d, who[u]) for u, p in g.where(set(who)).items() if u in who
                  and (d := math.dist((p[0] / g.map.T, p[2] / g.map.T), (cx, cz))) <= REACH)
    return now if not near or any(n == now for _, n in near) else near[0][1]


def close(g):
    """Remove the boss bar: the game ended (cheats.end), no countdown goes on."""
    if vars(g).pop("hill", {}).get("shown") is not None:
        g.command(f"bossbar remove {BAR}")


def tick(g, dt):
    """Count down the timer of the owner by dt game seconds, give the monument to a new owner, and end the game at 0."""
    if g.ended:
        return
    s = vars(g).setdefault("hill", {"owner": None, "left": YEARS * wonder.YEAR, "shown": None, "check": 0.0})
    if s["owner"] is not None:
        s["left"] -= dt
    s["check"] -= dt
    if s["check"] <= 0:
        s["check"] = EVERY
        if (n := owner(g, s["owner"])) != s["owner"]:
            from gather import allied                              # gather imports this module
            if s["owner"] is not None and not allied(g.players, n, s["owner"]):
                s["left"] = max(s["left"], RESET * wonder.YEAR)
            s["owner"] = n
            g.command("tellraw @a " + json.dumps({"text": f"Player {n} holds the monument.", "color": "yellow"}))
    if (n := s["owner"]) is None:
        return
    if s["left"] <= 0:
        from gather import allied                                  # gather imports this module
        return cheats.over(g, lambda m: allied(g.players, n, m))
    if s["shown"] is None:
        for c in (f'bossbar add {BAR} ""', f"bossbar set {BAR} color yellow", f"bossbar set {BAR} max {YEARS}",
                  f"bossbar set {BAR} players @a"):
            g.command(c)
    if (y := math.ceil(s["left"] / wonder.YEAR)) != s["shown"] or n != s.get("named"):   # a command only on a change
        s["shown"], s["named"] = y, n
        g.command(f"bossbar set {BAR} name " + json.dumps(f"Player {n}: monument, {y} year{'s' * (y != 1)} left"))
        g.command(f"bossbar set {BAR} value {y}")
