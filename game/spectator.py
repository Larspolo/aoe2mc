"""
The sidebar of the spectators (#2900, epic #2897), as the AoE2 DE spectator overlay: the resources and the population
of each player. A Minecraft player without a side is on the team spec (run.SPECTATORS, color gray, #2898), so the
objective aoe_spec goes into the display slot of that team color (Minecraft feature: one sidebar per team color). Each
player has the lines "P<N> Food", "P<N> Wood", "P<N> Gold", "P<N> Stone" and "P<N> Pop" (a holder name has no space:
the holder is p<N>_<name>, its display name has the space). The sidebar shows at most 15 lines: three players fit.
The sidebar of each player (Gather.board, Gather.sidebars) does not change. A player with the color gray (player 7)
keeps its own sidebar: then the spectators see none.

The player view (#2901): `/trigger aoe_view set N` lets a spectator look through the eyes of player N, as the player view
of the AoE2 DE spectator mode; `/trigger aoe_view set 0` is the free view again. Minecraft features: the trigger
objective aoe_view (a spectator may set it) and `spectate <target> <spectator>`: the camera follows the Minecraft player
of side N (run.Game.sides), else the town center of player N (its building target, combat.target_uuid), else its first
unit (a bot has no Minecraft player). The spectator gets the hide commands of the fog of player N (fog.update) for
itself only (`aoe hide NAME view`: the minimap dots and the team fog of the players do not change).

    spectator.tick(g)    # gather.Gather.run, once each second; fog.gathers(g): the person, its bots and the other persons
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fog  # noqa: E402

BOARD = "aoe_spec"
SLOT = "sidebar.team.gray"                                             # the color of the team spec (run.SPECTATORS)
EVERY = 1.0                                                            # seconds between two updates
NAMES = ("Food", "Wood", "Gold", "Stone")                              # the AoE2 order of the resource panel
VIEW = "aoe_view"                                                      # the trigger of the player view (#2901)


def lines(x):
    """The lines of the Gather x: {holder: (display name, value)}."""
    out = {f"p{x.player}_{r.lower()}": (f"P{x.player} {r}", x.stock[r.lower()]) for r in NAMES}
    out[f"p{x.player}_pop"] = (f"P{x.player} Pop", x.pop)
    return out


def tick(g):
    """Once each EVERY seconds: set each line of each Gather of the game that changed, one command per change. The
    first call makes the objective and shows it to the spectators."""
    if not hasattr(g, "clock") or g.clock() < vars(g).get("spectator_at", 0.0):   # a test loop with no clock
        return
    g.spectator_at = g.clock() + EVERY
    sides = fog.gathers(g)
    sent = vars(g).get("spectator_sent")
    if sent is None:
        g.spectator_sent = sent = {}
        g.command(f'scoreboard objectives add {BOARD} dummy "Players"')
        if all(x.color() != "gray" for x in sides):
            g.command(f"scoreboard objectives setdisplay {SLOT} {BOARD}")
    for x in sides:
        for holder, (name, n) in lines(x).items():
            if sent.get(holder) != n:
                if holder not in sent:
                    g.command(f"scoreboard players display name {holder} {BOARD} {json.dumps(name)}")
                g.command(f"scoreboard players set {holder} {BOARD} {n}")
                sent[holder] = n
    views(g)


def target(g, n):
    """The entity that the camera of the view of player n follows: the Minecraft player of side n, else the town
    center of player n, else its first unit; None when player n has none."""
    import combat
    if name := next((p for p, k in sorted(getattr(getattr(g, "game", None), "sides", {}).items()) if k == n), None):
        return name
    for o in g.data["objects"]:
        if o["kind"] == "building" and o["name"] == "TOWN_CENTER" and o["player"] == n and "footprint" in o:
            return combat.target_uuid([o["footprint"][i] for i in (0, 2, 1, 3)])
    h = next((h for h in fog.gathers(g) if h.player == n), None)
    units = [*h.villagers, *h.soldiers] * (h is not None)
    return next(iter(units + [o["uuid"] for o in g.data["objects"] if o["kind"] == "unit" and o["player"] == n
                              and o.get("uuid")]), None)


def hidden(g, h):
    """The enemy units that the player of the Gather h does not see: the fog of h (fog.tick), else one fog.update of
    its own (a bot has no fog tick). An empty set with no fog (not Paper, --reveal all, Spies)."""
    if not g.paper or getattr(g, "reveal", "normal") == "all" or "SPIES" in getattr(h, "techs", ()):
        return set()
    if vars(h).get("fog", {}).get("at") is None:                       # fog.tick never ran for h
        own, foe = fog.units(h)
        fog.update(h, h.where(set(own) | set(foe) | fog.targets(h)))
    return set(h.fog["hidden"])


def views(g):
    """The player view of each spectator: read the trigger aoe_view (N: player N, 0: the free view), then let the
    camera follow the target of player N and hide what player N does not see, only the changes."""
    names = sorted(getattr(getattr(g, "game", None), "spectators", ()))
    state = vars(g).get("spectator_views")
    if state is None:
        if not names:
            return
        g.spectator_views = state = {}
        g.command(f'scoreboard objectives add {VIEW} trigger "Player view"')
    g.command(f"scoreboard players enable @a[team=spec] {VIEW}")
    players = {h.player: h for h in fog.gathers(g)}
    if "passed" in (g.command(f"execute if entity @a[team=spec,scores={{{VIEW}=0..}}]") or ""):
        for name in names:
            m = re.search(r" has (-?\d+)", g.command(f"scoreboard players get {name} {VIEW}") or "")
            if not m or int(m[1]) < 0:
                continue
            g.command(f"scoreboard players set {name} {VIEW} -1")        # -1: no new choice
            old = state.pop(name, {"hidden": set()})
            if int(m[1]) in players:
                state[name] = {"player": int(m[1]), "target": None, "hidden": old["hidden"]}
                continue
            for c in fog.commands(g, "show", sorted(old["hidden"]), f"{name} view"):   # the free view shows all
                g.command(c)
            if "target" in old:
                g.command(f"execute as {name} run spectate")
    for name in [n for n in state if n not in names or state[n]["player"] not in players]:   # it took a side
        del state[name]                                                # (run.Game.choose), or player N left
    for name, v in state.items():
        h = players[v["player"]]
        if (t := target(g, v["player"])) != v["target"]:
            v["target"] = t
            if t:
                g.command(f"spectate {t} {name}")
        new = hidden(g, h)
        for c in fog.commands(g, "hide", sorted(new - v["hidden"]), f"{name} view") + \
                fog.commands(g, "show", sorted(v["hidden"] - new), f"{name} view"):
            g.command(c)
        v["hidden"] = new
