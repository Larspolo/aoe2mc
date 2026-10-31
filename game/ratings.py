"""The Elo rating of each human player (#5166, epic #5165). A game of 2 or more human teams changes the rating of each
player by the Elo rule (K = 32). A team uses the mean rating of its players. The ratings stay in RATING_FILE in the user
folder, for the next game. A game with bots only, or with one human team, changes nothing.
"""
import json
import os

RATING_FILE = os.path.join(os.path.expanduser("~"), ".aoe2mc", "ratings.json")   # {Minecraft name: rating} (#5166)
START, K = 1000, 32                                                               # the start rating and the Elo factor


def load(path=None):
    """{Minecraft name: rating} of the rating file."""
    try:
        with open(path or RATING_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def update(results, path=None):
    """Change the ratings by results = [(names, won)]: one entry per human team, with the Minecraft names of its players
    and won = True for the winner team. Returns [(name, old, new)] of the changed players. The team value is K times
    (score - expected); each player gets it. A team of other size than the average gets the value scaled, so that the
    changes of all teams sum to 0.
    """
    if len(results) < 2 or not any(won for _, won in results):
        return []
    table = load(path)
    mean = lambda xs: sum(xs) / len(xs)
    rate = [mean([table.get(n, START) for n in names]) for names, _ in results]
    expected = [mean([1 / (1 + 10 ** ((rate[o] - rate[t]) / 400)) for o in range(len(results)) if o != t])
                for t in range(len(results))]
    value = [K * ((1.0 if won else 0.0) - e) for (_, won), e in zip(results, expected)]
    shift = mean(value)                                                 # more than 2 teams: the sum is 0 again
    value = [v - shift for v in value]
    size = mean([len(names) for names, _ in results])
    out = []
    for (names, _), v in zip(results, value):
        for n in names:
            old = table.get(n, START)
            table[n] = old + v * size / len(names)
            out.append((n, old, table[n]))
    keep(table, path)
    return out


def keep(table, path=None):
    """Write the ratings into the rating file."""
    path = path or RATING_FILE
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(table, f)


def teams(g, one):
    """The human teams of game g as [(names, won)]: the Minecraft names of g.sides, grouped by the allies of the AoE2
    players (gather.allied). `one` is the player of the winner team (conquest.finish). A spectator has no player: no team."""
    from gather import allied  # gather imports the modules of the game
    groups = []
    for name, n in sorted(getattr(g, "sides", {}).items(), key=lambda kv: kv[1]):
        if not n:
            continue
        grp = next((x for x in groups if allied(g.players, x[0][1], n)), None)
        if grp is None:
            groups.append([(name, n)])
        else:
            grp.append((name, n))
    return [([name for name, _ in grp], allied(g.players, one, grp[0][1])) for grp in groups]


def announce(g, changes):
    """The chat shows each change, for example "Steve 1000 → 1016"."""
    for name, old, new in changes:
        g.command("tellraw @a " + json.dumps({"text": f"{name} {round(old)} → {round(new)}"}, ensure_ascii=False))
    if changes:
        tab(g)


def lore(name, table=None):
    """The lore line of the rating of a Minecraft player for the lobby item (#5167); "" with no rating (not START)."""
    r = (load() if table is None else table).get(name)
    return "" if r is None else f"Rating {round(r)}"


def tab(g, table=None):
    """The tab list shows the rating of each Minecraft player with a rating: the objective aoe_rating in the display slot
    list (a Minecraft feature, #5167). A player with no rating gets no score, so the tab list shows nothing."""
    table = load() if table is None else table
    g.command('scoreboard objectives add aoe_rating dummy "Rating"')
    g.command("scoreboard objectives setdisplay list aoe_rating")
    for name, r in sorted(table.items()):
        g.command(f"scoreboard players set {name} aoe_rating {round(r)}")
