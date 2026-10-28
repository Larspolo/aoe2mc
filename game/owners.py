"""The owners of the units that a game makes (#2992, epic #2991): the queues, the docks, the cheats, the game modes and
the herdables of a new town center. Gather.__init__ fills `enemies` once from the aoe2mc.json objects, so a new unit
goes into `enemies` of each other side here, and its player goes into one record that all Gathers of the game share
(run.play gives each Gather the same aoe2mc.json data). The aoe2mc.json key "owners" holds other data (#2940).

Minecraft knows the owner too (the tag aoe2mc.p<N> and the team p<N>: the mob AI fights by the alliances), but the
clicks and the orders read these tables: a team read at each click costs one RCON command."""
KEY = "unit_owners"                                                    # UUID -> player of a unit of the game


def add(g, uuid, name, player):
    """Keep player as the owner of the new unit uuid (AoE2 name) and make it an enemy of each side that is not its
    ally (gather.allied), as build.target does for a new building."""
    import build, gather                                               # gather -> train -> this module
    g.data.setdefault(KEY, {})[uuid] = player
    for o in build.sides(g):
        if not gather.allied(o.players, o.player, player):
            o.enemies[uuid] = name


def player(g, uuid):
    """The player of the unit uuid: its aoe2mc.json object, else the record of add(), else None."""
    return next((o.get("player") for o in g.data["objects"] if o.get("uuid") == uuid), g.data.get(KEY, {}).get(uuid))
