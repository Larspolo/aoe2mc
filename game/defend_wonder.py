"""
The AoE2 DE game mode "Defend the Wonder" in the game program (#2441, epic #2263; run.py --play --mode
defend-the-wonder): the player with the lowest number (player 1) starts with a complete Wonder next to its town center
and defends it; the other players, except its allies, attack it (AoE2 wiki "Defend the Wonder"). The Wonder stands for
the "wonder_years" of the line "defend-the-wonder" of game/data/setup.jsonl (250): then the defender and its allies
win (wonder.tick, the wonder victory). When the Wonder falls, the attackers win (tick). All players start in the
Post-Imperial Age (the key "age", as --age) with the resources of their side (the key "sides").
Only the players with a Gather (the people and the bot) play, as in empire_wars.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import cheats  # noqa: E402
import conquest  # noqa: E402
import table  # noqa: E402

MODE = next(r for r in table.load("setup.jsonl") if r["name"] == "defend-the-wonder")


def gathers(g):
    """{player: Gather} of the players that play: the Gather g of the people and the Gathers of the bots."""
    return {x.player: x for x in [g, *(s.g for s in getattr(g, "bots", ()))]}


def side(g, n):
    """The side of player n: "defender", "ally" (a team mate of the defender) or "attacker"."""
    from gather import allied                                          # gather imports this module
    return "defender" if n == g.defender else "ally" if allied(g.players, g.defender, n) else "attacker"


def setup(g, mode="defend-the-wonder", start=True):
    """Give the defender (the lowest player number with a Gather) its Wonder next to its town center for free, and each
    player the resources of its side. g: the Gather of player 1. start False (a loaded game, run.py): the Wonder and
    the resources are in the saved game, only find the Wonder site of the defender again."""
    import combat
    import train                                                       # train imports gather, gather imports build
    playing = gathers(g)
    g.defender = min(playing)
    x = playing[g.defender]
    tc = next((r for r, n in sorted(train.homes(x).items()) if n == "TOWN_CENTER"), None)
    if start and tc and (rect := build.near(x, "WONDER", ((tc[0] + tc[1]) // 2, (tc[2] + tc[3]) // 2))):
        build.rise(x, build.found(x, "WONDER", rect, free=True), float("inf"))   # complete at once
    if site := next((s for s in x.sites if s["name"] == "WONDER" and s.get("done")), None):
        x0, x1, z0, z1 = site["footprint"]
        g.wonder = combat.target_uuid([x0, z0, x1, z1])                # wonder.tick gives it its target
    for n, h in playing.items():
        h.stock.update(MODE["sides"][side(g, n)] if start else {})
    return g


def tick(g):
    """Each conquest.EVERY seconds: when the Wonder of the defender fell (wonder.tick saw its target go), the
    attackers win."""
    if g.ended or not vars(g).get("wonder") or g.clock() < vars(g).get("defend_at", 0.0):
        return
    g.defend_at = g.clock() + conquest.EVERY
    if g.wonder in vars(g).get("wonders_gone", ()):
        cheats.over(g, lambda n: side(g, n) == "attacker")
