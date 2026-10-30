"""
The technologies whose values depend on the own units near a unit (#4333, epic #4096, AoE2 DE wiki): the key "near" of
data/train.jsonl, {"if": [tests], "range": tiles, "per": units, "most": steps, "add": {field: n}, "part": {field: f}}.
An own unit that passes the tests (train.test) counts the other own units that pass them within range tiles; each per
of them give one step, at most most steps. Each step adds "add" to a field and "part" times the field (Saxon Shield
Wall: infantry +1/+1 armor for each 15 infantry within 7 tiles, at most +3/+3; Shu Coiled Serpent Array: the Spearman
line and White Feather Guards +0.5 % hit points for each one within 15 tiles, at most 30). train.stats with the UUID of
a unit reads its steps (g.near). A unit that loses hit points keeps its lost hit points, and at least 1 (the plugin
`aoe stats`, as the wiki says for Coiled Serpent Array).

Minecraft feature: none, Minecraft has no armor aura; the values go to the plugin with `aoe stats`. One pass every EVERY
AoE2 seconds counts with the positions of `aoe where` and sends `aoe stats` only for the units whose steps changed (few
RCON commands).

    near.tick(g, dt)        # gather.Gather.step: dt AoE2 seconds
"""
import civs
import numpy as np

EVERY = 5.0     # AoE2 seconds between two passes


def steps(g, pos):
    """{UUID: {technology: steps}} of the own soldiers at pos {UUID: (x, y, z)} for the researched technologies of g
    with the key "near"; a unit with no step is not in it."""
    import combat  # they import gather, gather imports this module
    import train
    out = {}
    for t, c in sorted(train.BY_KEY["near"].items()):
        us = sorted(u for u in pos if t in g.techs and (n := g.soldiers.get(u))
                    and any(train.test(x, n, combat.stats(n)) for x in c["if"]))
        if not us:
            continue
        p = np.array([pos[u] for u in us], float)[:, [0, 2]]
        near = (((p[:, None] - p[None]) ** 2).sum(-1) <= (c["range"] * g.map.T) ** 2).sum(1) - 1   # not itself
        for u, k in zip(us, np.minimum(near // c["per"], c["most"])):
            if k:
                out.setdefault(u, {})[t] = int(k)
    return out


def change(c, k, s):
    """The combat values s with k steps of the value c of the key "near"."""
    return s._replace(**{f: getattr(s, f) + n * k for f, n in c.get("add", {}).items()}) \
        ._replace(**{f: round(getattr(s, f) * (1 + p * k)) for f, p in c.get("part", {}).items()})


def tick(g, dt):
    """Count the own units near each own soldier of g, and send the new values of each unit whose steps changed."""
    import combat  # they import gather, gather imports this module
    import train
    if not vars(g).get("near") and not any(t in g.techs for t in train.BY_KEY["near"]):
        return
    g.near_time = vars(g).get("near_time", 0.0) + dt
    if g.near_time < EVERY:
        return
    g.near_time, old = 0.0, vars(g).get("near", {})
    g.near = steps(g, g.where(set(g.soldiers)))
    for u in sorted(set(old) | set(g.near)):
        if old.get(u) != g.near.get(u) and (name := g.soldiers.get(u)):
            g.command(combat.stats_command(u, name, train.stats(g, name, u), civs.taken(g, name), civs.friendly(g, name)))
