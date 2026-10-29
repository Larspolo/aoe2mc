"""The 9 AoE2 DE "Art of War" challenges (#3761, epic #3759): game/data/challenges.jsonl has the civilization, the goal,
the unlock order ("after") and the medal limits of each one (AoE2 wiki, one page per challenge). A limit is the largest
value that still gets the medal: game seconds of a "time" challenge, units lost of a "lost" challenge (the wiki "less
than 6 units lost" is a silver limit of 5).
run.py --play --challenge NAME (#3900, decision #3760: own challenge maps) plays one on a converted world: player 1
gets the civilization of the line, and tick() ends the game with the medal when the goal function of the key "check"
("module.function", (g, row) -> True when complete) says so; the key "setup" (the same form) places its start objects
(#3908). A new challenge is one data line and one goal function.
A challenge with the key "waves" sends enemy waves of player 2 to the town center, and a lost town center ends it
with no medal (#3907).
A challenge with the key "enemy" gets a bot town of player 2 that does not attack (setup, #3905).
A challenge opens after a medal in the challenge of its key "after" (#3904, AoE2 DE). The best medal of each one goes
into MEDAL_FILE in the user folder (the medals belong to the player, not to one map); `--challenge list` prints them.
Minecraft feature: a boss bar shows the goal and the next medal limit, a title shows the medal.

    challenge.tick(g)   # gather.Gather.run, when g.challenge is set
"""
import importlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table  # noqa: E402

CHALLENGES = {r["name"]: r for r in table.load("challenges.jsonl")}
MEDALS = ("gold", "silver", "bronze")
MEDAL_FILE = os.path.join(os.path.expanduser("~"), ".aoe2mc", "medals.json")   # {challenge: best medal} (#3904)
UNITS = {"lost": "units lost", "time": "game seconds"}             # the value of each kind of challenge


def medal(name, value):
    """The medal of challenge `name` for `value` (game seconds or units lost: less is better), else None."""
    c = CHALLENGES[name]
    return next((m for m in MEDALS if value <= c[m]), None)


def limits(name):
    """The medal limits of challenge `name` as text, for example "gold 480, silver 600, bronze 780 game seconds"."""
    c = CHALLENGES[name]
    return ", ".join(f"{m} {c[m]}" for m in MEDALS) + f" {UNITS[c['medal']]}"


def medals(path=None):
    """{challenge: best medal} of the medal file."""
    try:
        with open(path or MEDAL_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def keep(name, m, path=None):
    """Write medal m of challenge `name` into the medal file when it is better than the medal there."""
    path, best = path or MEDAL_FILE, medals(path)
    if m is None or (name in best and MEDALS.index(best[name]) <= MEDALS.index(m)):
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(best | {name: m}, f)


def opened(name, path=None):
    """True when challenge `name` is open: no key "after", or a medal in that challenge."""
    after = CHALLENGES[name].get("after")
    return after is None or after in medals(path)


def listing(path=None):
    """One line for each challenge in the order of the data file: its name, open or closed, its best medal."""
    best = medals(path)
    return [f"{n}: {'open' if opened(n, path) else 'closed'}, " + (f"{best[n]} medal" if n in best else "no medal")
            for n in CHALLENGES]


BAR = "aoe2mc:challenge"


def economy(g, c):
    """The goal of an economy challenge (the key "need" of its line): the resources in the stock, the villagers, the
    complete buildings and the number of ages."""
    import build, train                                             # they import gather, gather imports this module
    need, own = c["need"], train.owned(g)
    return all(g.stock[r] >= need[r] for r in ("food", "wood", "gold", "stone") if r in need) \
        and len(g.villagers) >= need.get("villagers", 0) and all(b in own for b in need.get("buildings", ())) \
        and build.ages(g) >= need.get("ages", 0)


def castle(g, c):
    """The goal of Fast Castle Age (the key "need" of its line): the villagers, the houses and the ages."""
    import build, train                                             # they import gather, gather imports this module
    need = c["need"]
    return len(g.villagers) >= need["villagers"] and train.owned(g).count("HOUSE") >= need["houses"] \
        and build.ages(g) >= need["ages"]


def town(g):
    """The block footprint (x0, x1, z0, z1) of the first own town center that stands, or None."""
    import train                                                    # train imports gather, gather imports this module
    return next((r for r, n in sorted(train.homes(g).items()) if n == "TOWN_CENTER"), None)


def defend(g, c):
    """The goal of Defending Against A Rush: the Castle Age while a town center stands."""
    import build                                                    # build imports gather, gather imports this module
    return build.ages(g) >= 2 and town(g) is not None


def waves(g, c, now):
    """Each wave of the key "waves" whose time came: summon its units of player 2 at the map corner that is farthest
    from the town center, and send them with `aoe attack` to the town center (Minecraft path finding, game/ai.py)."""
    import ai, combat, train                                        # they import gather, gather imports this module
    sent, tc = vars(g).get("challenge_waves", 0), town(g)
    while tc and sent < len(c["waves"]) and now >= c["waves"][sent]["at"]:
        far = lambda a, b: 2 if (a + b) / 2 > g.map.n / 2 else g.map.n - 3   # noqa: E731
        x, z = far(tc[0], tc[1]), far(tc[2], tc[3])
        pos = (x + 0.5, float(g.map.y(x, z)), z + 0.5)
        names = [n for n, k in sorted(c["waves"][sent]["units"].items()) for _ in range(k)]
        uuids = [train.summon(g, n, pos, player=2) for n in names]
        ai.attack(g, [u for u in uuids if u], [n for n, u in zip(names, uuids) if u], g.map.T,
                  combat.target_uuid([tc[0], tc[2], tc[1], tc[3]]))
        sent = g.challenge_waves = sent + 1


def besiege(g, c):
    """The setup of Destroying a Castle (#3908): a complete castle of player 2 with its defenders (the key "defenders")
    next to the town center of player 2 (else the middle of the map), and the start army of player 1 (the key "army")
    in front of its town center. g.siege_target: the target entity of the castle."""
    import build, combat, train                                     # they import gather, gather imports this module
    tc = next((o["footprint"] for o in g.data["objects"] if o["kind"] == "building" and o["player"] == 2
               and o["name"] == "TOWN_CENTER" and "footprint" in o), None)
    middle = ((tc[0] + tc[2]) // 2, (tc[1] + tc[3]) // 2) if tc else (g.map.n // 2, g.map.n // 2)
    if (rect := build.near(g, "CASTLE", middle, reach=24)) is None:
        return
    own, g.player = g.player, 2                                     # the site, its color and design of player 2
    try:
        site = build.found(g, "CASTLE", rect, free=True)
    finally:
        g.player = own
    build.rise(g, site, float("inf"))                               # complete at once: an enemy fort of player 1
    x0, x1, z0, z1 = rect
    g.siege_target = combat.target_uuid([x0, z0, x1, z1])
    home = next((r for r, n in sorted(train.homes(g).items()) if n == "TOWN_CENTER"), None)
    for player, front, key in ((2, rect, "defenders"), (g.player, home, "army")):
        cells = g.map.front(front) if front else []
        names = [n for n, k in sorted(c[key].items()) for _ in range(k)]
        for k, name in enumerate(names if cells else ()):
            x, z = cells[k % len(cells)]
            train.summon(g, name, (x + 0.5, float(g.map.y(x, z)), z + 0.5), player=player)


def siege(g, c):
    """The goal of Destroying a Castle: the castle of besiege() fell (Gather.free removes its target from g.forts)."""
    return "siege_target" in vars(g) and g.siege_target not in g.forts


def enemies(g):
    """The Gather of the enemy of the challenge (player 2, a bot), or None."""
    return next((s.g for s in getattr(g, "bots", ()) if s.g.player == 2), None)


def rush(g, c):
    """The goal of Rushing the Enemy: c["kills"] villagers of the enemy died (its losses, as recap.py counts them;
    the census names a villager VILLAGER)."""
    h = enemies(g)
    return h is not None and sum(n.startswith("VILLAGER") for n in vars(h).get("losses", {}).values()) >= c["kills"]


def setup(g):
    """The enemy town of challenge g.challenge (its key "enemy"), for free and complete at once: a town center when
    player 2 has none, the buildings near it and its villagers;
    first the function of its key "setup" (#3908). The bot of player 2 sends them to work."""
    import build, train                                             # they import gather, gather imports this module
    c, h = CHALLENGES[g.challenge], enemies(g)
    if "setup" in c:                                                # its start objects (besiege, #3908)
        module, _, function = c["setup"].rpartition(".")
        getattr(importlib.import_module(module), function)(g, c)
    if "enemy" not in c or h is None:
        return None
    e = c["enemy"]
    tc = next((r for r, n in sorted(train.homes(h).items()) if n == "TOWN_CENTER"), None)
    if tc is None and h.villagers and (rect := build.near(h, "TOWN_CENTER", next(iter(h.villagers.values())).cell)):
        build.rise(h, site := build.found(h, "TOWN_CENTER", rect, free=True), float("inf"))
        tc = site["footprint"]
    if tc is None:
        return None
    middle = ((tc[0] + tc[1]) // 2, (tc[2] + tc[3]) // 2)
    for name, count in sorted(e["buildings"].items()):
        for _ in range(count):
            if rect := build.near(h, name, middle):
                build.rise(h, build.found(h, name, rect, free=True), float("inf"))
    while len(h.villagers) < e["villagers"] and train.spawn(h, tc, "VILLAGER_MALE"):
        h.pop += 1
    return h


def done(g, c):
    """True when the goal of challenge row c is complete (its "check" function)."""
    module, _, function = c["check"].rpartition(".")
    return getattr(importlib.import_module(module), function)(g, c)


def close(g):
    """Remove the boss bar."""
    if vars(g).pop("challenge_shown", None) is not None:
        g.command(f"bossbar remove {BAR}")


def show(g, c, now):
    """The boss bar: the goal and the next medal limit ("Gold medal in 6:12"; a "lost" challenge, #3906: "2 units lost,
    silver medal up to 5", now is the units lost); commands only when the text changes."""
    left = next(((m, c[m] - now) for m in MEDALS if now <= c[m]), None)
    if c["medal"] == "lost":
        name = f"{int(now)} units lost, " + (f"{left[0]} medal up to {c[left[0]]}" if left else "no medal")
    else:
        name = f"{left[0].title()} medal in %d:%02d" % divmod(int(left[1]), 60) if left else "No medal"
    if vars(g).get("challenge_shown") is None:
        for cmd in (f'bossbar add {BAR} ""', f"bossbar set {BAR} color yellow", f"bossbar set {BAR} max {c['bronze']}",
                    f"bossbar set {BAR} players @a"):
            g.command(cmd)
    elif g.challenge_shown == name:
        return
    g.challenge_shown = name
    g.command(f"bossbar set {BAR} name " + json.dumps(f"{c['goal']}: {name}"))
    g.command(f"bossbar set {BAR} value {max(0, min(int(now), c['bronze']))}")


def tick(g):
    """End the game of challenge g.challenge with its medal when the goal is complete, or with no medal after the
    bronze limit of a time challenge; else show the boss bar."""
    if g.ended:
        return
    import cheats
    from recap import game_time
    c, now = CHALLENGES[g.challenge], game_time(g)
    if "waves" in c:                                                # the enemy attacks (#3907)
        waves(g, c, now)
    complete = done(g, c)
    m = medal(g.challenge, now if c["medal"] == "time" else len(vars(g).get("losses", {})))   # "lost": score.fallen
    if complete or (c["medal"] == "time" and m is None) or ("waves" in c and town(g) is None):
        close(g)
        g.command(f'title @a[team=p{g.player}] subtitle ' + json.dumps(
            {"text": f"{m.title()} medal" if complete and m else "No medal", "color": "yellow"}))
        g.medal = m if complete else None
        keep(g.challenge, g.medal)
        return cheats.over(g, lambda p: p == g.player and complete and m is not None)
    show(g, c, now if c["medal"] == "time" else len(vars(g).get("losses", {})))
