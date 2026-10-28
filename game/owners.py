"""The owners of the units that a game makes (#2992, epic #2991): the queues, the docks, the cheats, the game modes and
the herdables of a new town center. Gather.__init__ fills `enemies` once from the aoe2mc.json objects, so a new unit
goes into `enemies` of each other side here, and its player goes into one record that all Gathers of the game share
(run.play gives each Gather the same aoe2mc.json data). The aoe2mc.json key "owners" holds other data (#2940).

Minecraft knows the owner too (the tag aoe2mc.p<N> and the team p<N>: the mob AI fights by the alliances), but the
clicks and the orders read these tables: a team read at each click costs one RCON command."""
import math

KEY = "unit_owners"                                                    # UUID -> player of a unit of the game


def add(g, uuid, name, player):
    """Keep player as the owner of the new unit uuid (AoE2 name) and make it an enemy of each side that is not its
    ally (gather.allied), as build.target does for a new building."""
    import build, gather                                               # gather -> train -> this module
    g.data.setdefault(KEY, {})[uuid] = player
    for o in build.sides(g):
        if not gather.allied(o.players, o.player, player):
            o.enemies[uuid] = name


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
            for group in o.groups.values():
                group.discard(uuid)
            if uuid in o.selected:                                     # the old owner cannot give it orders now
                o.selected.discard(uuid)
                o.command(f"data merge entity {uuid} {{Glowing:0b}}")
                o.command(f"tag {uuid} remove {gather.SELECT}")
            if not gather.allied(o.players, o.player, new):
                o.enemies[uuid] = name
        elif gather.soldier(name):
            o.soldiers[uuid] = name
        elif uuid not in o.villagers and (pos := o.pos(uuid)):
            o.villagers[uuid] = gather.Villager(uuid, pos)
            o.units.append({"kind": "unit", "name": name, "player": new, "uuid": uuid,
                            "tile": [math.floor(pos[0]) / o.map.T, math.floor(pos[2]) / o.map.T]})


def player(g, uuid):
    """The player of the unit uuid: its aoe2mc.json object, else the record of add(), else None."""
    return next((o.get("player") for o in g.data["objects"] if o.get("uuid") == uuid), g.data.get(KEY, {}).get(uuid))
