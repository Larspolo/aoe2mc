"""The AoE2 achievements in the game program (#5279, epic #5277): grant(g, n, key) gives the advancement
aoe2mc:<key> of data/achievements.jsonl (written by aoe2mc.advancement_files, #5278) to the Minecraft players of
player n. Minecraft shows the toast and the chat line (/advancement grant). A bot (share set) has no Minecraft player.
Events (the key "event" of a line): "win" or "win <CIV>" (cheats.over, each player with won(n)); "age <TECH>" with an
optional "before" in game seconds (recap.aged, train.research). An optional "civ" (a key of game/data/civs.jsonl) and
"mode" (a game mode of game/data/setup.jsonl, gather.has_mode) limit a line to that civilization and mode (#5281). "win all" needs the wins of earlier games: not here.
"count:train" with "units" and "need" (#5280): the player trained `need` units of these names in this game
(train.tick, at each trained unit: the count changes only there).
"research <TECH>" (train.research, #5629), "build <BUILDING>" (build.grow: a complete own building), "autoscout"
(autoscout.start), "train <UNIT> at <BUILDING>" (train.tick) and "win ai <level>" (cheats.over: a win while a bot of
that bots.LEVELS name lost).
"kill" with "killed" and "by" (#5640): the player killed a unit of "killed" with a unit of "by" (kills, once per tick: the
kill log of the plugin, Kills.java). An item is a unit name, a group of civs.GROUPS, or groups joined by "+" (all of them).
The state of a win (#5644): "win homeless" (demolish.delete of the first own TOWN_CENTER of the scenario), "win only"
with "units" (the player trained units in this game, all of these names) and "win ally" (an allied player, gather.allied).
"destroy WONDER" with "before" in years (wonder.tick: an enemy wonder fell with less years left) and "lose site <BUILDING>"
with "least", a part of 1 (demolish.unfound: an own site of at least that progress went)."""
import functools
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import civs  # noqa: E402

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "achievements.jsonl")
ROWS = [json.loads(x) for x in open(PATH, encoding="utf-8") if x.strip()]


def grant(g, n, key):
    """Grant aoe2mc:<key> to the team of player n, once per player and key, only for a key of ROWS."""
    done = vars(g).setdefault("achieved", set())
    if (n, key) in done or key not in {r["name"].lower() for r in ROWS}:
        return
    done.add((n, key))
    g.command(f"advancement grant @a[team=p{n}] only aoe2mc:{key}")


def matches(g, h, r):
    """True when the civilization of the player of h and the game mode of g match the "civ" and "mode" keys of line r."""
    if "civ" in r and not (hasattr(h, "data") and civs.real(h, h.player) == r["civ"]):
        return False
    return "mode" not in r or getattr(g, "mode", None) == r["mode"] or r["mode"] in getattr(g, "modes", ())


def event(g, h, name, seconds=None):
    """Grant each line whose event is `name` (and whose civ and mode match) to the player of Gather h (not a bot).
    seconds: a value that must be under the "before" and at least the "least" of the line."""
    if getattr(h, "share", None) or not hasattr(g, "command"):    # a bot, or a test double with no server
        return
    for r in ROWS:
        if (r.get("event") == name and (seconds is None or r.get("least", -1) <= seconds < r.get("before", float("inf")))
                and matches(g, h, r)):
            grant(g, h.player, r["name"].lower())


def won(g, h, levels=()):
    """The win of the player of h; levels: the difficulties of the bots that lost (#5629)."""
    event(g, h, "win")
    if hasattr(h, "data") and (civ := civs.real(h, h.player)):
        event(g, h, f"win {civ}")
    for level in sorted(levels):
        event(g, h, f"win ai {level}")
    if vars(h).get("homeless"):
        event(g, h, "win homeless")
    made = set(vars(h).get("train_counts", {}))
    for r in ROWS:
        if (r.get("event") == "win only" and made and made <= set(r["units"]) and not getattr(h, "share", None)
                and hasattr(g, "command") and matches(g, h, r)):
            grant(g, h.player, r["name"].lower())
    import gather  # gather -> train -> this module
    players = getattr(h, "players", None) or {}
    if any(int(m) != h.player and gather.allied(players, h.player, int(m)) for m in players):
        event(g, h, "win ally")


def aged(g, name, seconds):
    event(g, g, f"age {name}", seconds)


def trained(g, name, at=None):
    """Grant the line "train <name> at <at>" (at: the building that trained it, #5629). Count a unit name that g (a Gather) trained, and grant each "count:train" line whose units reach its need."""
    counts = vars(g).setdefault("train_counts", {})
    counts[name] = counts.get(name, 0) + 1
    if at:
        event(g, g, f"train {name} at {at}")
    if getattr(g, "share", None) or not hasattr(g, "command"):
        return
    for r in ROWS:
        if (r.get("event") == "count:train" and name in r["units"] and matches(g, g, r)
                and sum(counts.get(u, 0) for u in r["units"]) >= r["need"]):
            grant(g, g.player, r["name"].lower())


@functools.lru_cache(maxsize=None)
def type_names():
    """{AoE2 unit ID: name}: the type tags aoe2mc.t<ID> of the kill log (units.make_entity)."""
    import units
    return {v: k for k, v in units.type_ids().items()}


def unit_name(g, key):
    """The AoE2 name of a unit of the kill log: t<ID> of its type tag, else the UUID of a building (g.fort_names)."""
    if re.fullmatch(r"t\d+", key):
        return type_names().get(int(key[1:]))
    return getattr(g, "fort_names", {}).get(key)


def member(name, items):
    """True when unit name is one of items: a name, a group of civs.GROUPS, or groups joined by "+" (all of them).
The state of a win (#5644): "win homeless" (demolish.delete of the first own TOWN_CENTER of the scenario), "win only"
with "units" (the player trained units in this game, all of these names) and "win ally" (an allied player, gather.allied).
"destroy WONDER" with "before" in years (wonder.tick: an enemy wonder fell with less years left) and "lose site <BUILDING>"
with "least", a part of 1 (demolish.unfound: an own site of at least that progress went)."""
    import combat  # combat -> gather -> train -> this module
    return name is not None and any(name == i or all(p in civs.GROUPS and civs.GROUPS[p](name, combat.stats(name))
                                                     for p in i.split("+")) for i in items)


def killed(h, name, by):
    """Grant each "kill" line whose "killed" has the killed unit name and whose "by" has the killer to the player of h."""
    if getattr(h, "share", None) or not hasattr(h, "command"):
        return
    for r in ROWS:
        if r.get("event") == "kill" and member(name, r["killed"]) and member(by, r["by"]) and matches(h, h, r):
            grant(h, h.player, r["name"].lower())


def kills(g):
    """Read the new kills of the plugin ("aoe kills": "Kills: p1 t42 p2 t331; ...", the killer and the killed unit,
    Kills.java) and give each kill of an enemy unit to the side of its killer. Gather.run, once per tick; no command
    when no line has the event "kill", or for a Gather with no player (a test of the loop). The bots read nothing: player 1
    reads for all sides."""
    if getattr(g, "share", None) or not getattr(g, "player", None) or not any(r.get("event") == "kill" for r in ROWS):
        return
    import build  # build -> gather -> train -> this module
    import gather
    sides = {o.player: o for o in build.sides(g)}
    for kill in (g.command("aoe kills") or "").partition("Kills:")[2].split(";"):
        f = kill.split()
        a, b = (re.fullmatch(r"p(\d+)", x) for x in f[0:3:2]) if len(f) == 4 else (None, None)
        h = a and sides.get(int(a[1]))
        if h and b and not gather.allied(getattr(h, "players", {}), h.player, int(b[1])):
            killed(h, unit_name(g, f[3]), unit_name(g, f[1]))
