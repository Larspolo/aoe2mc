"""
The AoE2 DE game mode "Defend the Wonder" in the game program (#2441, epic #2263; run.py --play --mode
defend-the-wonder): the player with the lowest number (player 1) starts with a complete Wonder next to its town center
and defends it; the other players, except its allies, attack it (AoE2 wiki "Defend the Wonder"). The Wonder stands for
the "wonder_years" of the line "defend-the-wonder" of game/data/setup.jsonl (250): then the defender and its allies
win (wonder.tick, the wonder victory). When the Wonder falls, the attackers win (tick). All players start in the
Post-Imperial Age (the key "age", as --age) with the resources of their side (the key "sides"). Each attacker also
starts with the complete buildings of the key "side_buildings" (a Castle), and the base of each player has a closed ring
of complete Stone Walls with one gate (the key "ring", #2462; wiki: "the bases are surrounded by Stone Walls, like in
the map Arena").
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
    from gather import allied  # gather imports this module
    return "defender" if n == g.defender else "ally" if allied(g.players, g.defender, n) else "attacker"


def setup(g, mode="defend-the-wonder", start=True):
    """Give the defender (the lowest player number with a Gather) its Wonder next to its town center for free, and each
    player the resources of its side. g: the Gather of player 1. start False (a loaded game, run.py): the Wonder and
    the resources are in the saved game, only find the Wonder site of the defender again."""
    import combat
    import train  # train imports gather, gather imports build
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
        h.show_stock()                                                 # the board holds the stock too (#3111)
        home = next((r for r, k in sorted(train.homes(h).items()) if k == "TOWN_CENTER"), None)
        if start and home:
            middle = ((home[0] + home[1]) // 2, (home[2] + home[3]) // 2)
            for name, count in sorted(MODE["side_buildings"].get(side(g, n), {}).items()):
                for _ in range(count):
                    if rect := build.near(h, name, middle):
                        build.rise(h, build.found(h, name, rect, free=True), float("inf"))
            ring(h, middle)
    return g


def ring_tiles(cx, cz, r):
    """The tiles of a square ring with the radius r (tiles) around the tile (cx, cz), and the gate spots in it: for each
    side (south, north, east, west) (tiles, way) of 4 tiles in the middle of the side, as build.gate_spot."""
    tiles = [(x, z) for x in range(cx - r, cx + r + 1) for z in range(cz - r, cz + r + 1) if max(abs(x - cx), abs(z - cz)) == r]
    gates = [([(cx - 2 + i, cz + k * r) for i in range(4)], False) for k in (1, -1)] \
        + [([(cx + k * r, cz - 2 + i) for i in range(4)], True) for k in (1, -1)]
    return tiles, gates


def ring(g, middle):
    """Put a closed ring of complete Stone Walls with one gate around the town center of g with its middle block, for
    free. A tile that is not free (a tree, a mine, a building, the border) stays out: it blocks the way too. The radius
    (the key "ring") leaves room for the houses and the drop sites. Returns the sites."""
    T, cfg = g.map.T, MODE["ring"]
    rect = lambda t: (t[0] * T, (t[0] + 1) * T, t[1] * T, (t[1] + 1) * T)   # noqa: E731
    tiles, gates = ring_tiles(middle[0] // T, middle[1] // T, cfg["radius"])
    door = next(((t, way) for t, way in gates if all(build.free(g, rect(c)) for c in t)), None)
    out = []
    if door:
        t, way = door
        x0, z0 = min(t)
        out.append(build.found(g, cfg["gate"], (x0 * T, (max(t)[0] + 1) * T, z0 * T, (max(t)[1] + 1) * T), way, t,
                               free=True))
    out += [build.found(g, cfg["wall"], rect(c), free=True) for c in tiles
            if not (door and c in door[0]) and build.free(g, rect(c))]
    for site in out:
        build.rise(g, site, float("inf"))                              # complete at once
    return out


def tick(g):
    """Each conquest.EVERY seconds: when the Wonder of the defender fell (wonder.tick saw its target go), the
    attackers win."""
    if g.ended or not vars(g).get("wonder") or g.clock() < vars(g).get("defend_at", 0.0):
        return
    g.defend_at = g.clock() + conquest.EVERY
    if g.wonder in vars(g).get("wonders_gone", ()):
        cheats.over(g, lambda n: side(g, n) == "attacker")
