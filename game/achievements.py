"""The AoE2 achievements in the game program (#5279, epic #5277): grant(g, n, key) gives the advancement
aoe2mc:<key> of data/achievements.jsonl (written by aoe2mc.advancement_files, #5278) to the Minecraft players of
player n. Minecraft shows the toast and the chat line (/advancement grant). A bot (share set) has no Minecraft player.
The key "event" of a line names the event that grants it (a list: any of them). The optional keys of a line, their
types and what they do: data/achievement_keys.jsonl. "civ" and "mode" limit a line to a civilization and a game mode
(matches, #5281). "win all" needs the wins of earlier games: not here.
The docstring of each function names its event kinds. A plain event name (`event`) is at its call:
`grep -rn "achievements.event" game` (for example "research <TECH>" in train.research).

Parallel tickets conflicted at the end of this text, in won, in killed and in the key tables of the tests (#5781). So a
new achievement changes no shared line here:
- a data line, and for a new key one line in data/achievement_keys.jsonl (the tests read it);
- a new plain event: `achievements.event(g, h, "NAME")` at the place of the event;
- a new test of a line at a win or a kill: a function `@on("win", KIND)` or `@on("kill", KIND)`, not a branch of won or
  killed;
- a new field of a Gather for a saved game: `field("NAME")` (SAVED, savegame.KEPT), not a line of savegame.py;
- a new function: after the function that it is nearest to, not at the end of the file; its docstring names its event
  kinds, not this text; its tests go into a new file tests/test_achievements_<topic>.py."""
import functools
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "achievements.jsonl")
ROWS = [json.loads(x) for x in open(PATH, encoding="utf-8") if x.strip()]
ON = {}      # {source: {event kind: test (g, h, r, **at) -> bool}}: the lines of a win or a kill (on, run)
SAVED = []   # the fields of a Gather that the achievements keep in a saved game (field, savegame.KEPT)


def field(name):
    """Register name as a field of a Gather that a saved game keeps (savegame.KEPT). Returns name."""
    SAVED.append(name)
    return name


def on(source, kind):
    """Register a test (g, h, r, **at) -> bool of the lines of event kind at the event source ("win": won, "kill":
    killed). The line is granted when its civ and mode match and the test is true."""
    def add(test):
        ON.setdefault(source, {})[kind] = test
        return test
    return add


def kinds(r):
    e = r.get("event")
    return e if isinstance(e, list) else [e]


def run(source, g, h, **at):
    """Grant to the player of Gather h (not a bot) each line whose event kind has a test of source that is true."""
    if getattr(h, "share", None) or not hasattr(g, "command"):    # a bot, or a test double with no server
        return
    tests = ON.get(source, {})
    for r in ROWS:
        mine = [tests[k] for k in kinds(r) if k in tests]
        if mine and matches(g, h, r) and any(test(g, h, r, **at) for test in mine):
            grant(g, h.player, r["name"].lower())


def grant(g, n, key):
    """Grant aoe2mc:<key> to the team of player n, once per player and key, only for a key of ROWS."""
    done = vars(g).setdefault("achieved", set())
    if (n, key) in done or key not in {r["name"].lower() for r in ROWS}:
        return
    done.add((n, key))
    g.command(f"advancement grant @a[team=p{n}] only aoe2mc:{key}")


def matches(g, h, r):
    """True when the civilization of the player of h and the game mode of g match the "civ" and "mode" keys of line r."""
    import civs  # civs loads a rule table: savegame imports this module before the rule set (test_antiquity_data)
    if "civ" in r and not (hasattr(h, "data") and civs.real(h, h.player) == r["civ"]):
        return False
    return "mode" not in r or getattr(g, "mode", None) == r["mode"] or r["mode"] in getattr(g, "modes", ())


def event(g, h, name, seconds=None):
    """Grant each line whose event is `name` (and whose civ, mode and limits match) to the player of Gather h (not a
    bot). seconds: the value of the event for the limits "before" and "least" (between)."""
    if getattr(h, "share", None) or not hasattr(g, "command"):    # a bot, or a test double with no server
        return
    for r in ROWS:
        if name in kinds(r) and all(test(h, r, seconds) for test in LIMITS) and matches(g, h, r):
            grant(g, h.player, r["name"].lower())


LIMITS = []   # the tests (h, r, seconds) -> bool of the line r of a plain event (limit, event)


def limit(test):
    """Register a test (h, r, seconds) -> bool that each line of a plain event must pass (a new optional key)."""
    LIMITS.append(test)
    return test


@limit
def between(h, r, seconds):
    """"before" and "least" (#5644): the value is under "before" and at least "least": game seconds ("age <TECH>",
    recap.aged), years left ("destroy WONDER", wonder.tick) or a part of 1 ("lose site <BUILDING>", demolish.unfound)."""
    return seconds is None or r.get("least", -1) <= seconds < r.get("before", float("inf"))


@limit
def villagers(h, r, seconds):
    """"villagers" (#5642): the player has that many live villagers (Golden Spurs)."""
    return len(getattr(h, "villagers", ())) >= r.get("villagers", 0)


def counted(g, kind, key, names, n):
    """Grant each "count:<kind>" line of g (a Gather, not a bot) whose key has a name of names and whose need is n(r) or less."""
    if getattr(g, "share", None) or not hasattr(g, "command"):
        return
    for r in ROWS:
        if r.get("event") == f"count:{kind}" and set(names) & set(r[key]) and matches(g, g, r) and n(r) >= r["need"]:
            grant(g, g.player, r["name"].lower())


BUILT = field("build_counts")   # {building name, "<name> by <builder>": count} (#5642)


def built(g, name, by=()):
    """"count:build" with "buildings", "need" and an optional "by" (builder names, #5642): the player completed `need`
    buildings of these names in this game. Count a complete own building name of g and its builder names by
    (gather.Gather.step), and grant the lines."""
    counts = vars(g).setdefault(BUILT, {})
    for k in {name, *(f"{name} by {b}" for b in set(by))}:
        counts[k] = counts.get(k, 0) + 1
    counted(g, "build", "buildings", [name], lambda r: sum(
        counts.get(f"{b} by {u}" if "by" in r else b, 0) for b in r["buildings"] for u in r.get("by", [None])))


def queued(g, q, ages):
    """"count:queue" with "units", "need" and "ages" (the highest age index, build.ages; #5642): grant each line whose
    units are `need` times in the queue q of g (train.queue), in an age up to its "ages"."""
    counted(g, "queue", "units", [e["name"] for e in q], lambda r: -1 if ages > r["ages"] else
            sum(e["name"] in r["units"] for e in q))


def won(g, h, levels=()):
    """The win of the player of h (cheats.over): "win", "win <CIV>" and "win ai <level>" (levels: the bots.LEVELS names
    of the bots that lost, #5629), then the lines of the tests of source "win" (on)."""
    import civs
    event(g, h, "win")
    if hasattr(h, "data") and (civ := civs.real(h, h.player)):
        event(g, h, f"win {civ}")
    for level in sorted(levels):
        event(g, h, f"win ai {level}")
    run("win", g, h)


HOMELESS = field("homeless")   # demolish.delete of the first own TOWN_CENTER of the scenario (#5644)


@on("win", "win homeless")
def homeless(g, h, r):
    """"win homeless" (#5644): the player lost the first own TOWN_CENTER of the scenario (demolish.delete)."""
    return bool(vars(h).get(HOMELESS))


@on("win", "win only")
def only(g, h, r):
    """"win only" with "units" (#5644): the player trained units in this game, all of these names."""
    made = set(vars(h).get(TRAINED, {}))
    return bool(made) and made <= set(r["units"])


@on("win", "win ally")
def ally(g, h, r):
    """"win ally" (#5644): the player has an allied player (gather.allied)."""
    import gather  # gather -> train -> this module
    players = getattr(h, "players", None) or {}
    return any(int(m) != h.player and gather.allied(players, h.player, int(m)) for m in players)


def aged(g, name, seconds):
    """"age <TECH>" with an optional "before" in game seconds (recap.aged, train.research; #5309)."""
    event(g, g, f"age {name}", seconds)


TRAINED = field("train_counts")   # {unit name: count} (#5280)


def trained(g, name, at=None):
    """Grant the line "train <name> at <at>" (at: the building that trained it, #5629; train.tick). "count:train" with
    "units" and "need" (#5280): count a unit name that g (a Gather) trained, and grant each line whose units reach its
    need (the count changes only here)."""
    counts = vars(g).setdefault(TRAINED, {})
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
    """True when unit name is one of items: a name, a group of civs.GROUPS, or groups joined by "+" (all of them)."""
    import civs
    import combat  # combat -> gather -> train -> this module
    return name is not None and any(name == i or all(p in civs.GROUPS and civs.GROUPS[p](name, combat.stats(name))
                                                     for p in i.split("+")) for i in items)


def killed(h, name, by):
    """A kill of the unit name by the unit by of the player of h (kills): grant the lines of the tests of source "kill"
    (on). An item of "killed" and "by" is a unit name, a group of civs.GROUPS, or groups joined by "+" (member)."""
    run("kill", h, h, name=name, by=by)


@on("kill", "kill")
def one_kill(g, h, r, name, by):
    """"kill" with "killed" and "by" (#5640): the player killed a unit of "killed" with a unit of "by"."""
    return member(name, r["killed"]) and member(by, r["by"])


KILLED = field("kill_counts")   # {line name: count} (#5641)


@on("kill", "count:kill")
def kill_count(g, h, r, name, by):
    """"count:kill" with "by", "need" and an optional "killed" and "age" (#5641): the player killed `need` units (of
    "killed") with units of "by" in this game, only while in the ages up to "age"."""
    if not (member(by, r["by"]) and ("killed" not in r or member(name, r["killed"])) and ("age" not in r or ages(h) <= r["age"])):
        return False
    counts = vars(h).setdefault(KILLED, {})
    counts[r["name"]] = counts.get(r["name"], 0) + 1
    return counts[r["name"]] >= r["need"]


def ages(h):
    import build  # build -> gather -> train -> this module
    return build.ages(h)


def kills(g):
    """Read the new kills of the plugin ("aoe kills": "Kills: p1 t42 p2 t331; ...", the killer and the killed unit,
    Kills.java) and give each kill of an enemy unit to the side of its killer. Gather.run, once per tick; no command
    when no line has the event "kill", or for a Gather with no player (a test of the loop). The bots read nothing: player 1
    reads for all sides."""
    if getattr(g, "share", None) or not getattr(g, "player", None) or not any(k in ON.get("kill", {}) for r in ROWS for k in kinds(r)):
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


def explored(g, n, count):
    """"explore" with "tiles" and "part" (#5646; fog.minimap, no revealed map): grant each line whose map size "tiles"
    n reaches (480: Ludicrous, game/data/per_names.jsonl) and whose "part" of the n x n tiles count explored reaches."""
    if getattr(g, "share", None) or not hasattr(g, "command"):
        return
    for r in ROWS:
        if r.get("event") == "explore" and n >= r["tiles"] and count >= r["part"] * n * n and matches(g, g, r):
            grant(g, g.player, r["name"].lower())


GATHERED = field("gather_counts")   # {"<what> <age index>": amount} (#5643)


def gathered(g, what, amount=1):
    """"count:gather" with "gather" and "need" and an optional "age" (#5643): count amount of what that the player of g
    (a Gather) gathered, per age (0: the Dark Age, build.ages), and grant each line of what whose count of the ages up
    to its "age" reaches its need. what: a hunted animal name (gather.Gather.hunt: one at its death, when it leaves its
    carcass for the player), "FOLWARK" (the food of build.folwark), a "trickle" technology (its food, feitoria.tick) or
    "KESHIK" (its gold, spoils.attacks)."""
    import build  # build -> gather -> train -> this module
    counts = vars(g).setdefault(GATHERED, {})
    key = f"{what} {build.ages(g)}"
    counts[key] = counts.get(key, 0) + amount
    if getattr(g, "share", None) or not hasattr(g, "command"):
        return
    for r in ROWS:
        if (r.get("event") == "count:gather" and r["gather"] == what and matches(g, g, r)
                and sum(v for k, v in counts.items() if k.rpartition(" ")[0] == what
                        and int(k.rpartition(" ")[2]) <= r.get("age", 9)) >= r["need"] - 1e-9):
            grant(g, g.player, r["name"].lower())
