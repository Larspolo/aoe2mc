"""The owners of the units that a game makes (#2992, epic #2991): the queues, the docks, the cheats, the game modes and
the herdables of a new town center. Gather.__init__ fills `enemies` once from the aoe2mc.json objects, so a new unit
goes into `enemies` of each other side here, and its player goes into one record that all Gathers of the game share
(run.play gives each Gather the same aoe2mc.json data). The aoe2mc.json key "owners" holds other data (#2940).

Minecraft knows the owner too (the tag aoe2mc.p<N> and the team p<N>: the mob AI fights by the alliances), but the
clicks and the orders read these tables: a team read at each click costs one RCON command."""
import math

KEY = "unit_owners"                                                    # UUID -> player of a unit of the game
KILLED = "killed_units"                                                # UUIDs that the program killed (#2996)


def add(g, uuid, name, player):
    """Keep player as the owner of the new unit uuid (AoE2 name) and make it an enemy of each side that is not its
    ally (gather.allied), as build.target does for a new building."""
    import build, gather                                               # gather -> train -> this module
    g.data.setdefault(KEY, {})[uuid] = player
    for o in build.sides(g):
        if not gather.allied(o.players, o.player, player):
            o.enemies[uuid] = name


def killed(g, uuids):
    """Keep uuids as killed by the program (battle_royale.start, cheats.destroy): update_enemies keeps them out."""
    if hasattr(g, "data"):
        g.data.setdefault(KILLED, set()).update(uuids)


def give_building(g, target, new):
    """Give the enemy building target to player new on each side of the game (Redemption, #2994): its owner (fort_players),
    its box in forts of each side that is not new, and its construction site (train.homes reads the sites of the Gather
    of the owner)."""
    import build, combat                                               # build imports gather, gather imports this module
    sides = build.sides(g)
    box = next((o.forts[target] for o in sides if target in o.forts), None)
    for o in sides:
        vars(o).setdefault("fort_players", {})[target] = new
        o.forts.pop(target, None)
        if box is not None and o.player != new:
            o.forts[target] = box
        for s in [s for s in o.sites if o.player != new and combat.target_uuid(site_box(s)) == target]:
            o.sites.remove(s)
            s["player"] = new
            next(x for x in (g, *sides) if x.player == new).sites.append(s)


def give(g, uuid, new):
    """Give the unit uuid to player new in the tables of the program (a conversion, #2993): each other side drops it
    from its units, selection (glow, tag), groups, farms and ships, the new owner takes it as a soldier or a villager
    (gather.soldier; fleet.ship makes the entry of a ship at its first use), `enemies` of each side follows the
    alliances, and its owner record is new. The commands to the world (tag, team, name color) stay with the caller."""
    import build, gather                                               # gather -> train -> this module
    sides = build.sides(g)
    known = [*(o.enemies for o in sides), *(o.soldiers for o in sides),
             *({u.get("uuid"): u["name"]} for u in [*g.data["objects"], *(u for o in sides for u in o.units)])]
    name = next((t[uuid] for t in known if uuid in t), "")
    obj = next((o for o in g.data["objects"] if o.get("uuid") == uuid), None)
    if obj is None:
        g.data.setdefault(KEY, {})[uuid] = new
    else:
        obj["player"] = new
    for o in sides:
        o.enemies.pop(uuid, None)
        if o.player != new:
            for table in (o.villagers, o.soldiers, o.ships):
                table.pop(uuid, None)
            o.units[:] = [u for u in o.units if u.get("uuid") != uuid]
            for t in [t for t, f in o.farmers.items() if f == uuid]:
                del o.farmers[t]
            for groups in vars(o).get("person_groups", {}).values():   # the groups of each person (#3490)
                for group in groups.values():
                    group.discard(uuid)
            if uuid in o.others() | o.selected:                         # the old owner cannot give it orders now
                o.drop(uuid)
                o.command(f"data merge entity {uuid} {{Glowing:0b}}")
                o.command(f"tag {uuid} remove {gather.SELECT}")
            if new and not gather.allied(o.players, o.player, new):
                o.enemies[uuid] = name
            elif not new and (gather.hunt_food(name) or gather.predator(name)):   # Gaia: an animal is prey (#2998)
                o.prey[uuid] = name
        elif gather.soldier(name):
            o.soldiers[uuid] = name
        elif uuid not in o.villagers and (pos := o.pos(uuid)):
            o.villagers[uuid] = gather.Villager(uuid, pos)
            o.units.append({"kind": "unit", "name": name, "player": new, "uuid": uuid,
                            "tile": [math.floor(pos[0]) / o.map.T, math.floor(pos[2]) / o.map.T]})


def player(g, uuid):
    """The player of the unit uuid: its aoe2mc.json object, else the record of add(), else None."""
    return next((o.get("player") for o in g.data["objects"] if o.get("uuid") == uuid), g.data.get(KEY, {}).get(uuid))


def site_box(site):
    """The footprint of a construction site in the order of combat.target_uuid (build.target)."""
    x0, x1, z0, z1 = site["footprint"]
    return [x0, z0, x1, z1]


def update_enemies(g):
    """Compute `enemies` of each side again after a change of the stances in g.players (#2996: scenario.diplomacy,
    conquest.last_man, diplomacy.change, savegame.load): the units of the aoe2mc.json objects and of the owner record,
    with their present player, that are not of an ally, not of Gaia, not herdable (herd.take: prey, not an enemy) and
    not killed by the program."""
    import build, gather, herd                                              # gather -> train -> this module
    sides = [o for o in (build.sides(g) if hasattr(g, "peers") else [g]) if hasattr(o, "enemies")]   # also a stub of a test
    if not sides or not hasattr(g, "data"):
        return
    names = {u: k for o in sides for u, k in o.enemies.items()}
    units = {o["uuid"]: (o["name"], o["player"]) for o in g.data["objects"] if o["kind"] == "unit" and o.get("uuid")}
    for u, n in g.data.get(KEY, {}).items():                           # the units of the game: their name of a table
        units[u] = (units.get(u, ("", 0))[0] or names.get(u) or next((o.soldiers[u] for o in sides if u in o.soldiers), ""), n)
    dead = g.data.get(KILLED, set())
    for o in sides:
        o.enemies.clear()                                              # in place: other tables can hold it
        o.enemies.update({u: k for u, (k, n) in units.items() if n and u not in dead and not herd.herdable(k)
                          and not gather.allied(o.players, o.player, n)})
