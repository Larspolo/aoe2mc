"""
A Gaia unit that is not an animal (a villager, soldier, monk, trade cart or ship of a scenario) joins the first player
whose unit comes near it (#5108, part of #5107). As in AoE2 (AoE2 wiki, "Gaia": Gaia units "are converted to the
player whose unit comes close to them first"). The wiki gives no distance: 2 tiles, as herd.RANGE. With units of more
players near it in the same look, herd.owner decides (the most units, then the lowest number). A unit with the key
`unconvertible` (set_gaia_unconvertible of a random map, #5074) stays Gaia: the DE random map scripting guide makes
the Gaia units "unconvertible", and a join is a conversion without a monk.

Minecraft feature: teams (`team join`) and the tag aoe2mc.pN, as monk.take. The nearness rule is own logic: Minecraft
has no "owner by nearness" rule.

    gaia.tick(g)    # gather.Gather.run: once each EVERY seconds, for the player and its bots, on Paper only
"""
import json
import math

import herd
import owners

EVERY = herd.EVERY
RANGE = herd.RANGE


def joinable(o):
    """True for a Gaia unit of the map that joins a player: not an animal, not unconvertible."""
    import gather  # gather imports this module
    n = o["name"]
    return (o["kind"] == "unit" and o.get("player") == 0 and bool(o.get("uuid")) and not o.get("unconvertible")
            and not herd.herdable(n) and not gather.hunt_food(n) and not gather.predator(n))


def tick(g):
    """Look each EVERY seconds which player has units near each Gaia unit, and give it to that player."""
    if not g.paper:
        return
    state = vars(g).setdefault("gaia", {"at": None})
    now = g.clock()
    if state["at"] is not None and now - state["at"] < EVERY:
        return
    state["at"] = now
    gathers = [g, *(b.g for b in g.bots)]
    dead = set().union(*(h.dead for h in gathers), *(us for h in gathers for us in vars(h).get("garrisons", {}).values()))
    free = {o["uuid"]: o for o in g.data["objects"] if joinable(o) and o["uuid"] not in dead}
    if not free:
        return
    mine = {u: h.player for h in gathers for u in [*h.villagers, *h.soldiers]}
    pos = g.where(set(mine) | set(free))
    T, reach = g.map.T, RANGE * g.map.T
    for u, o in sorted(free.items()):
        at = pos.get(u)
        if at is None and "tile" in o:                             # a Gaia unit has no team: `aoe where` skips it
            at = (o["tile"][0] * T, 0.0, o["tile"][1] * T)
        if at is None:
            continue
        counts = {}
        for v, p in pos.items():
            if v in mine and math.dist((p[0], p[2]), (at[0], at[2])) <= reach:
                counts[mine[v]] = counts.get(mine[v], 0) + 1
        if (new := herd.owner(counts, 0)) != 0:
            join(g, o, new)


def join(g, o, new):
    """Give the Gaia unit o to player new: its tag, team and name color, and those of its horse or crew (as
    monk.take), its old order stops, the tables of all sides (owners.give), and a chat line to the new player."""
    import units
    u = o["uuid"]
    for run in ("", f"execute as {u} on vehicle run ", f"execute as {u} on passengers run "):
        who = "@s" if run else u
        for cmd in (f"tag {who} remove aoe2mc.p0", f"tag {who} add aoe2mc.p{new}", f"team join p{new} {who}"):
            g.command(run + cmd)
    color = units.HEX.get(g.players.get(str(new), {}).get("color", ""), "#FFFFFF")
    g.command(f'data modify entity {u} CustomName.color set value "{color}"')
    g.command(f"aoe stop {u}")
    owners.give(g, u, new)
    o["player"] = new
    g.command(f"tellraw @a[team=p{new}] " + json.dumps({"text": f"A {units.pretty(o['name'])} joins you.", "color": "gold"}))
