"""
The end of a game of the game program (#2660), as the end screen of AoE2 DE (the "Achievements" tabs: score, military,
economy, technology, society, timeline): cheats.over gives each person a recap book in hotbar slot 0, and the items
that give orders leave the hotbar (the wand, the control groups, "Go to", the Game menu: all carrot_on_a_stick items,
and the selection wand of vanilla). The map in the off-hand and the scenario book stay: they only show.
The pages: the result, the score and the game time; the score parts of each player (score.points); and for each player
its units (trained, alive, lost), buildings (built, lost), technologies and the game times of its ages.
Minecraft features: a written book (scenario.written), `clear` and `item replace entity`. A bot has no book, but its
pages are in the book of each person, also after its defeat (cheats.ruin keeps its Gather in g.fallen_bots, #3281).

    recap.give(g, won)        # cheats.over, after the titles
    recap.aged(g, name)       # train.research: the game time of an age
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import civs  # noqa: E402
import fog  # noqa: E402
import score  # noqa: E402
import train  # noqa: E402

SLOT = "hotbar.0"                                                      # key 1: the first item of the hotbar
ORDERS = ("carrot_on_a_stick", "warped_fungus_on_a_stick")             # the items that give orders (gather.WAND)
STATE = ("players", "soldiers", "techs", "t0", "trained", "villagers")   # the fields of a Gather that parts reads


def game_time(g):
    """The game seconds since the start of the session (gather.NORMAL game seconds per real second at speed 1).
    A pause (pause.py) stops the game time: it stays at the time of the pause (#3377)."""
    from gather import NORMAL  # gather imports train, train this module
    main = getattr(getattr(g, "game", None), "g", None) or g           # the Gather of player 1 holds the pause
    now = main.paused_at if getattr(main, "paused", False) else g.clock()
    return (now - g.t0) * NORMAL * getattr(g, "speed", 1.0)


def mmss(seconds):
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def aged(g, name):
    """Keep the game time of age technology name of g (the timeline of AoE2)."""
    vars(g).setdefault("age_times", {})[name] = game_time(g)
    import achievements  # the AoE2 achievements of an age (#5279)
    achievements.aged(g, name, g.age_times[name])


def parts(g, won):
    """The pages of the recap book of the game of g, won(player) as in cheats.over: [(title or None, text)]. Each
    player of the map (with objects or a Gather) has its result; a player with a Gather (a person or a bot) also has its score and values."""
    sides = fog.gathers(g)
    sides += [h for h in vars(g).get("fallen_bots", ()) if all(h is not o for o in sides)]   # defeated bots (#3281)
    points = score.points(g, sides)
    gone = {u for h in sides for u in vars(h).get("razed", {})}
    placed = {o.get("player") for o in g.data.get("objects", ())}       # not the empty player slots of a scenario
    out = [("Recap", f"Game time: {mmss(game_time(g))}\n\n" + "\n".join(
        f"Player {n}{f' ({c.title()})' if (c := civs.civ(g, n)) not in (None, 'RANDOM') else ''}: "
        f"{'Victory' if won(n) else 'Defeat'}" + (f", score {score.total(points[n])}" if n in points else "")
        for n in sorted(int(p) for p in g.players if int(p) and (int(p) in points or int(p) in placed))))]
    out.append(("Score", "\n\n".join(f"Player {h.player}\n" + "\n".join(
        f"{p.title()}: {int(points[h.player][p])}" for p in score.PARTS) for h in sides)))
    for h in sides:
        lost = vars(h).get("losses", {})
        alive = sum(u not in lost for u in (*h.villagers, *h.soldiers))
        fell = vars(h).get("buildings_lost", [])                   # deleted or razed, also start buildings (#3736)
        built = sum(own for _, own in [*score.buildings(h, set()), *fell])
        fallen = built - sum(own for _, own in score.buildings(h, gone)) - sum(own for _, own in fell) + len(fell)
        given = vars(h).get("given", set())
        techs = sorted(train.ITEMS[t][2] for t in h.techs if t not in given and t not in build.AGE_TECHS and t in train.ITEMS)
        ages = vars(h).get("age_times", {})
        out.append((f"Player {h.player}", "\n".join([
            f"Units: {sum(n + 1 for n in h.trained.values())} trained, {alive} alive, {len(lost)} lost",
            f"Buildings: {built} built, {fallen} lost",
            f"Ages: {', '.join(f'{train.ITEMS[a][2]} {mmss(t)}' for a, t in sorted(ages.items(), key=lambda x: x[1])) or 'none'}",
            f"Technologies: {len(techs)}" + "".join(f"\n- {t}" for t in techs)])))
    return out


def give(g, won):
    """Each person of the game of g: the order items leave its inventory, and the recap book goes into SLOT."""
    import scenario  # scenario imports gather: import it late
    if not all(hasattr(h, k) for h in fog.gathers(g) for k in STATE):  # a partial Gather of a test: no game
        return
    pages = parts(g, won)
    for h in fog.gathers(g):
        if getattr(h, "share", None):                                  # a bot has no Minecraft player
            continue
        who = f"@a[team=p{h.player}]"
        for item in ORDERS:
            g.command(f"clear {who} minecraft:{item}")
        for cmd in scenario.written(who, SLOT, "Recap", pages):
            g.command(cmd)
