"""
The fall of an own building in the game program (#3008, epic #3006). At 0 hit points the plugin removes the target
entity of a building and fills its box with air (AoePlugin.hit, combat.building); this module lets its owner stop
using it within about one second: its menu does not open and its units do not come out (train.homes), its population
room and its count for the age rules go (train.owned), the units inside come out (garrison.holders, garrison.tick),
and its queue goes. AoE2 gives back the cost of the units and technologies in the queue of a destroyed building, as a
cancel of them (train.cancel).
A complete construction site leaves g.sites. A start building of aoe2mc.json stays in g.data["objects"] (all sides
share it, scenario.fallen and the minimap read it): its footprint goes into g.ruins, which train.homes, train.owned
and garrison.holders skip, and the save keeps it (savegame.py).
Only a building whose target was in an earlier answer falls: a farm, a fish trap, a wonder before wonder.tick, or the
"lasting" monastery of Capture the Relic has no target (build.target) and never falls. A new building on the footprint
of a fallen one gets the same target UUID (combat.target_uuid), so a fall forgets the UUID. The candidates come from
the present owner of each building (o["player"]): a building that a monk converts leaves the list of its old owner.

Minecraft feature: the target entities on the team p<n> of the player, read with one `aoe where` for each WHERE_PAGE
targets (Gather.where, #1470). Vanilla has no plugin that takes hit points, so no building falls there.

    ruins.tick(g)    # gather.Gather.step: once each EVERY seconds, for each side (the person and each bot), Paper only
"""
EVERY = 1.0             # real seconds between two looks (fog.EVERY: the same `aoe where` cost)


def own(g):
    """{target UUID: block footprint (x0, x1, z0, z1)} of the complete own buildings of the player that still stand
    for it: the start ones not in g.ruins and the complete construction sites."""
    import combat                                                  # combat imports gather, which imports this module
    out = {combat.target_uuid(o["footprint"]): (x0, x1, z0, z1) for o in g.data["objects"]
           if o["kind"] == "building" and o["player"] == g.player and "footprint" in o and not fallen(g, o)
           for x0, z0, x1, z1 in [o["footprint"]]}
    return out | {combat.target_uuid([x0, z0, x1, z1]): (x0, x1, z0, z1) for s in g.sites
                  if s.get("done") and s["player"] == g.player for x0, x1, z0, z1 in [s["footprint"]]}


def fallen(g, o):
    """True when the start building o of aoe2mc.json fell for the player of g (g.ruins)."""
    x0, z0, x1, z1 = o.get("footprint", (None,) * 4)
    return (x0, x1, z0, z1) in getattr(g, "ruins", ())


def tick(g):
    """Each EVERY seconds: an own building whose target was in an earlier answer and is not in this one fell."""
    if not getattr(g, "paper", False) or g.clock() < vars(g).get("ruins_at", 0.0):
        return
    g.ruins_at = g.clock() + EVERY
    live = g.where(None, f"@e[tag=aoe2mc.building,team=p{g.player},tag=!aoe2mc.wall]")   # walls: no home, no room
    seen = vars(g).setdefault("ruins_seen", set())
    for uuid, rect in own(g).items():
        if uuid in live:
            seen.add(uuid)
        elif uuid in seen:
            seen.discard(uuid)                                     # a new building on the footprint has the same UUID
            fall(g, rect)


def fall(g, rect):
    """The own building with block footprint rect fell: a complete site leaves g.sites, a start building goes into
    g.ruins, its queue goes with its cost back, and the units inside come out."""
    import build, combat, fleet, garrison, train                   # they import gather, which imports this module
    sites = [s for s in g.sites if s.get("done") and s["player"] == g.player and tuple(s["footprint"]) == rect]
    if sites:
        g.sites = [s for s in g.sites if all(s is not t for t in sites)]
    else:
        g.ruins.add(rect)
    for e in g.queues.pop(rect, []):
        for r, v in e.get("paid", train.COSTS[e["name"]]).items():   # as train.cancel: a free technology gives nothing
            g.stock[r] += v
            g.command(f"scoreboard players add {r.capitalize()} {g.board} {v}")
    if g.garrisons.get(rect):
        garrison.out(g, rect)
    x0, x1, z0, z1 = rect
    y = combat.building_box({"footprint": [x0, z0, x1, z1]}, g.map.ground)[1]
    for m in {id(h.map): h.map for h in [g, *build.sides(g)]}.values():   # the ground and the drop sites of each side
        m.unbuild(rect, y)
    for v in g.villagers.values():                                 # a load goes to another drop site, or the villager stops
        if v.state == "to_drop":
            g.go(v, "to_drop", g.drop_goals(v))
    fleet.reroute(g)
