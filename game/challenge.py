"""The 9 AoE2 DE "Art of War" challenges (#3761, epic #3759): game/data/challenges.jsonl has the civilization, the goal,
the unlock order ("after") and the medal limits of each one (AoE2 wiki, one page per challenge). A limit is the largest
value that still gets the medal: game seconds of a "time" challenge, units lost of a "lost" challenge (the wiki "less
than 6 units lost" is a silver limit of 5).
run.py --play --challenge NAME (#3900, decision #3760: own challenge maps) plays one on a converted world: player 1
gets the civilization of the line, and tick() ends the game with the medal when the goal function of the key "check"
("module.function", (g, row) -> True when complete) says so. A new challenge is one data line and one goal function.
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


def done(g, c):
    """True when the goal of challenge row c is complete (its "check" function)."""
    module, _, function = c["check"].rpartition(".")
    return getattr(importlib.import_module(module), function)(g, c)


def close(g):
    """Remove the boss bar."""
    if vars(g).pop("challenge_shown", None) is not None:
        g.command(f"bossbar remove {BAR}")


def show(g, c, now):
    """The boss bar: the goal and the next medal limit ("Gold medal in 6:12"); commands only when the text changes."""
    left = next(((m, c[m] - now) for m in MEDALS if now <= c[m]), None)
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
    complete = done(g, c)
    m = medal(g.challenge, now) if c["medal"] == "time" else None
    if complete or (c["medal"] == "time" and m is None):
        close(g)
        g.command(f'title @a[team=p{g.player}] subtitle ' + json.dumps(
            {"text": f"{m.title()} medal" if complete and m else "No medal", "color": "yellow"}))
        g.medal = m if complete else None
        keep(g.challenge, g.medal)
        return cheats.over(g, lambda p: p == g.player and complete and m is not None)
    show(g, c, now)
