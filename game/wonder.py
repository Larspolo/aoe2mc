"""
The AoE2 wonder victory in the game program (#1137, epic #1134): a player who keeps a complete wonder for the wonder
timer wins. A wonder of the scenario (it has the target entity of combat.building) and a complete construction site
WONDER of a player (tick() gives it a target, so units can destroy it) start a countdown. Each wonder has its own
countdown; the boss bar of a player shows the lowest one to all players, as AoE2 shows it (Minecraft feature: one
`bossbar` per player). When the target of a wonder is gone (the plugin removes it at 0 hit points, or cheats.destroy),
its countdown stops; without another wonder the bar of the player goes. At the end of the game all bars go (close).
The timer is in AoE2 years (1 year = 5 game seconds) and depends on the map size (AoE2 wiki, "Wonder": 200 years up to
Medium, 300 Normal, 350 Large, 400 Huge). The program counts game time: tick() adds dt (game seconds) at each call,
gather.Gather.run gives it tick × NORMAL, as for the training queues. At the end, the owner wins: the human player sees
"Victory" for its own wonder and "Defeat" for a wonder of a rival; the game then ends (g.ended).
A game mode with the key "wonder_years" in game/data/setup.jsonl has that timer (Defend the Wonder: 250, #2441; Wonder
Race: 0, the completion of the first wonder wins, #2406).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cheats  # noqa: E402
import table  # noqa: E402

YEAR = 5.0           # game seconds of one AoE2 year
YEARS = ((168, 200), (200, 300), (220, 350), (math.inf, 400))   # (largest map size in tiles, years)
EVERY = 3.0          # seconds between two checks of the targets
RACE = {r["name"]: r["wonder_years"] for r in table.load("setup.jsonl") if "wonder_years" in r}   # mode -> years


def years(size):
    """The years of the wonder timer on a map of size tiles (miniature maps: as Tiny)."""
    return next(y for s, y in YEARS if (size or 0) <= s)


def rivals(g, n, key):
    """The values of key (data/train.jsonl) of the technologies of the enemies of player n in the game of g (Atheism,
    #4336): all Gathers of the game (fog.gathers of conquest.main) that are no allies of n."""
    import train
    from conquest import main
    from fog import gathers                                            # fog imports gather, which imports this module
    from gather import allied
    return [v for h in gathers(main(g)) if not allied(g.players, n, h.player)
            for t in sorted(getattr(h, "techs", ())) if (v := train.value(key, t)) is not None]


def later(g, t):
    """Add the years of the enemies' technologies (key "rival_years") to the victory timer t of a player, also to a
    timer that runs at the research (Atheism, #4336). Returns the added game seconds when they changed, else None."""
    more = sum(rivals(g, t["player"], "rival_years")) * YEAR
    if more == t.get("later", 0.0):
        return None
    t["left"], t["later"] = t["left"] + more - t.get("later", 0.0), more
    return more


def bar(n):
    return f"aoe2mc:wonder_p{n}"


def found(g):
    import combat
    """The complete wonders of the players: {target uuid: (player, site or None)}."""
    out = {combat.target_uuid(o["footprint"]): (o["player"], None) for o in g.data["objects"]
           if o["kind"] == "building" and o["name"] == "WONDER" and o["player"] and "footprint" in o}
    for s in [s for b in [g, *(b.g for b in getattr(g, "bots", ()))] for s in b.sites]:   # a bot.Bot: its Gather
        if s["name"] == "WONDER" and s.get("done"):
            x0, x1, z0, z1 = s["footprint"]
            out[combat.target_uuid([x0, z0, x1, z1])] = (s["player"], s)
    return out


def close(g):
    """Remove the boss bars of all players: the game ended (cheats.end), no countdown goes on (#1178)."""
    for n in vars(g).pop("wonder_shown", {}):
        g.command(f"bossbar remove {bar(n)}")


def tick(g, dt):
    """Count down the wonders by dt game seconds, stop the ones whose target is gone, and end the game at 0."""
    if g.ended:
        return
    import combat                                                      # combat -> gather -> wonder: import it late
    timers, gone = vars(g).setdefault("wonders", {}), vars(g).setdefault("wonders_gone", set())
    shown = vars(g).setdefault("wonder_shown", {})                     # player -> years on its bar
    for t in timers.values():
        t["left"] -= dt
    if g.clock() >= vars(g).get("wonder_at", 0.0):                     # not each tick: one command per wonder
        g.wonder_at = g.clock() + EVERY
        for uuid in [u for u in timers if "passed" not in g.command(f"execute if entity {u}")]:
            n = timers.pop(uuid)["player"]
            gone.add(uuid)
            g.command("tellraw @a " + json.dumps({"text": f"The wonder of player {n} is destroyed.", "color": "red"}))
            if not any(t["player"] == n for t in timers.values()):
                g.command(f"bossbar remove {bar(n)}")
                shown.pop(n, None)
        total = RACE.get(g.mode, years(g.data.get("map_size"))) * YEAR
        for uuid, (n, site) in found(g).items():
            if uuid in timers or uuid in gone:
                continue
            if site:                                                   # a built wonder: a target of attacks
                x0, x1, z0, z1 = site["footprint"]
                g.forts[uuid] = box = combat.building_box({"footprint": [x0, z0, x1, z1]}, g.map.ground)
                for c in combat.building(uuid, "WONDER", n, box):
                    g.command(c)
            elif "passed" not in g.command(f"execute if entity {uuid}"):
                continue                                               # not loaded yet, or no target
            timers[uuid] = {"player": n, "left": total}
            if n not in shown:
                for c in (f'bossbar add {bar(n)} ""', f"bossbar set {bar(n)} color yellow",
                          f"bossbar set {bar(n)} max {int(total / YEAR)}", f"bossbar set {bar(n)} players @a"):
                    g.command(c)
                shown[n] = None
            g.command("tellraw @a " + json.dumps({"text": f"Player {n} built a wonder.", "color": "yellow"}))
    for t in timers.values():
        if (more := later(g, t)) is not None:
            g.command(f"bossbar set {bar(t['player'])} max {int((RACE.get(g.mode, years(g.data.get('map_size'))) * YEAR + more) / YEAR)}")
    for n in sorted({t["player"] for t in timers.values()}):
        left = min(t["left"] for t in timers.values() if t["player"] == n)
        if left <= 0:
            from gather import allied                               # gather imports this module
            return cheats.over(g, lambda m: allied(g.players, n, m))   # n and its allies win (#1936)
        if (y := math.ceil(left / YEAR)) != shown.get(n):                # a command only when the years change
            shown[n] = y
            g.command(f"bossbar set {bar(n)} name " + json.dumps(f"Player {n}: wonder, {y} year{'s' * (y != 1)} left"))
            g.command(f"bossbar set {bar(n)} value {y}")
