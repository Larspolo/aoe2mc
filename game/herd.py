"""
The capture of herdable animals (#1792, epic of the owner feedback in a demo, 2026-10-27). As in AoE2 (AoE2 wiki,
"Herdable animal"): "a player gains control of a herdable animal if one of their units moves close to it", and with
units of more players near it, "the player who has the most units nearby" gets it. A herdable stays with its owner
while a unit of the owner is near. "Close" is the line of sight of a herdable: 2 tiles (the same page).

Minecraft feature: teams (`team join`), the tag aoe2mc.pN, the `CustomName` color and the `Color` of a sheep (as
monk.take). The nearness rule is own logic: Minecraft has no "owner by nearness" rule.

    herd.tick(g)    # gather.Gather.run: once each EVERY seconds, for the player and its bots, on Paper only
"""
import math

import civs

EVERY = 1.0             # real seconds between two looks (fog.EVERY: the same `aoe where` cost)
RANGE = 2               # tiles: the line of sight of a herdable (AoE2 wiki, "Herdable animal")


def herdable(name):
    import gather                                                  # gather imports this module
    return ("COW" if name.startswith("COW_") else name) in gather.HERDS


def owner(counts, old, celts=()):
    """The new owner of a herdable from {player: own units near it}, or old: the owner keeps it while one of its units
    is near; else the player with the most units near (the lowest number on a tie: the same in each run). A Celt player
    (in celts) takes it also next to units of its owner (AoE2 wiki, "Herdable animal", #1825); a Celt owner keeps it
    from another Celt by the first rule, so that it does not change between two Celt players each look."""
    if counts.get(old) and old not in celts:
        counts = {p: n for p, n in counts.items() if p in celts and p != old}
    if not counts or counts.get(old):
        return old
    return min(counts, key=lambda p: (-counts[p], p))


def tick(g):
    """Look each EVERY seconds which player has units near each herdable, and give it to its new owner (capture)."""
    if not g.paper:
        return
    state = vars(g).setdefault("herd", {"at": None})
    now = g.clock()
    if state["at"] is not None and now - state["at"] < EVERY:
        return
    state["at"] = now
    gathers = [g, *(b.g for b in g.bots)]
    dead = set().union(*(h.dead for h in gathers))
    herds = {o["uuid"]: o for o in g.data["objects"] if o["kind"] == "unit" and o.get("uuid")
             and herdable(o["name"]) and o["uuid"] not in dead}
    if not herds:
        return
    mine = {u: h.player for h in gathers for u in [*h.villagers, *h.soldiers]}
    pos = g.where(set(mine) | set(herds))
    T, reach = g.map.T, RANGE * g.map.T
    for u, o in sorted(herds.items()):
        at = pos.get(u)
        if at is None and not o["player"] and "tile" in o:         # a Gaia herdable has no team: `aoe where` skips
            at = (o["tile"][0] * T, 0.0, o["tile"][1] * T)         # it, and it does not walk (NoAI)
        if at is None:
            continue
        counts = {}
        for v, p in pos.items():
            if v in mine and math.dist((p[0], p[2]), (at[0], at[2])) <= reach:
                counts[mine[v]] = counts.get(mine[v], 0) + 1
        celts = {p for p in counts if civs.civ(g, p) == "CELTS"}
        if (new := owner(counts, o["player"], celts)) != o["player"]:
            take(g, gathers, o, new)


def take(g, gathers, o, new):
    """Give the herdable o to player new: its tag, team, name color and wool, and the lists of each Gather (prey,
    enemies, selection, hunters)."""
    import gather, units
    u, old = o["uuid"], o["player"]
    o["player"] = new
    if old:
        g.command(f"tag {u} remove aoe2mc.p{old}")
    g.command(f"tag {u} add aoe2mc.p{new}")
    g.command(f"team join p{new} {u}")
    color = units.HEX.get(g.players.get(str(new), {}).get("color", ""), "#FFFFFF")
    g.command(f'data modify entity {u} CustomName.color set value "{color}"')
    if "Color" in (units.classify(o["name"]) or {}):                # a sheep or goat: the wool of its player (#1790)
        dye = units.dye(new, {int(k): v for k, v in g.players.items() if k.isdigit()})
        g.command(f"data modify entity {u} Color set value {dye}b")
    for h in gathers:
        h.prey.pop(u, None)
        h.enemies.pop(u, None)
        if h.player == new:
            h.prey[u] = o["name"]
        elif not gather.allied(h.players, h.player, new):
            h.enemies[u] = o["name"]
        if h.player != new and u in h.selected:                    # the old owner cannot give it orders now
            h.selected.discard(u)
            h.command(f"data merge entity {u} {{Glowing:0b}}")
            h.command(f"tag {u} remove {gather.SELECT}")
        for v in h.villagers.values():
            if v.prey == u and h.player != new:                    # its hunters stop
                v.prey, v.path = None, []
                h.set(v, "idle")
