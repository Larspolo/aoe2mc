"""
The Follow and Guard orders of the stance menu (#3358, epic #3353 items 4 and 5), as the AoE2 buttons: the selected
military units walk after an own or allied unit and stay near it (Follow), or stay near a unit or an own building and
attack the enemies that come near it (Guard). The live replay has the same orders (replay.Replay.follows, #2551).
g.follows: follower UUID -> [target UUID or building rect (x0, x1, z0, z1), "follow" or "guard"].
"""
import json
import math

import lang

TRAIL = 3                      # tiles: a follower farther than this from its target walks to it again (replay.TRAIL)
GUARD = 5                      # tiles: a guard attacks the nearest enemy this near its target


def start(g, player, kind, target):
    """Give the selected military units the order kind ("follow" or "guard") on the target (a UUID or a rect)."""
    units = [u for u in sorted(g.selected) if u in g.soldiers and u != target]
    if not units:
        return
    g.new_order(units)                                             # it ends the old follows of the units too
    follows = vars(g).setdefault("follows", {})
    for u in units:
        follows[u] = [target, kind]
    tick(g)


def refuse(g, player, kind):
    """A click that does not hit a target of the pending order: a line in the action bar, the order ends."""
    text = lang.text("aoe2mc.follow.refuse_follow" if kind == "follow" else "aoe2mc.follow.refuse_guard")
    g.command(f"title {player} actionbar " + json.dumps(text))


def end(g, units):
    """A new order ends the follows of the units."""
    follows = vars(g).get("follows", {})
    for u in set(units) & follows.keys():
        del follows[u]


def spot(target, pos):
    """The feet position of the target: its unit position, or the middle of its building rect; None when dead."""
    if isinstance(target, str):
        return pos.get(target)
    x0, x1, z0, z1 = target
    return ((x0 + x1) / 2, None, (z0 + z1) / 2)


def tick(g):
    """Walk each follower that is farther than TRAIL tiles from its target to it; a guard attacks the nearest enemy
    in GUARD tiles of its target. A dead follower or a dead target ends the entry."""
    follows = vars(g).get("follows")
    if not follows:
        return
    targets = {t for t, _ in follows.values() if isinstance(t, str)}
    guards = any(k == "guard" for _, k in follows.values())
    pos = g.positions(sorted(set(follows) | targets | (set(g.enemies) if guards else set())))
    T = g.map.T
    for u, (t, kind) in sorted(follows.items()):
        p, s = pos.get(u), spot(t, pos)
        if p is None or s is None:
            del follows[u]
            continue
        if kind == "guard":
            near = [(math.hypot(q[0] - s[0], q[2] - s[2]), e) for e in sorted(g.enemies) if (q := pos.get(e))]
            near = [n for n in near if n[0] <= GUARD * T]
            if near:
                g.command(f"aoe attack {u} {min(near)[1]}")
                continue
        if math.hypot(p[0] - s[0], p[2] - s[2]) > TRAIL * T:
            x, z = math.floor(s[0]), math.floor(s[2])
            g.command(f"aoe moveto {u} {x} {g.map.y(x, z) if s[1] is None else math.floor(s[1])} {z}")
