"""The trebuchet in the game program (#1351, epic #1348): it packs and unpacks as in AoE2 DE (AoE2 wiki "Trebuchet":
"Cannot attack when packed. Cannot move when unpacked. Takes 11.1 seconds to pack and unpack."). An attack order
unpacks it: it stops at once and shoots after PACK AoE2 seconds. A target out of its range: it walks packed until the
target is in range, then it unpacks (#1400; unpacked, it packs first). A move order packs it: it walks after PACK
seconds. A new trebuchet, and one of the map, is packed.

Minecraft feature: the trebuchet stays the same minecart on its carrier (#836). Unpacked: movement_speed 0 on the
carrier (`aoe speed`) and its AoE2 range (`aoe range`, combat.range_command); packed: the walk speed and range 0, so
the plugin lets it shoot nothing.
The armor changes when a pack or an unpack ends, as in AoE2 DE (wiki: 2 melee and 8 pierce armor packed, 1 and 150
unpacked, #1409): the same `aoe stats` command as the technologies (stats_command).
The warden in the minecart (#1664) gets its size of the state at the same time (`attribute ... minecraft:scale`).

    trebuchet.unpack(g, u, target)   # gather.Gather.attack: the trebuchet u attacks target after the walk and unpack
    trebuchet.move(g, u, cmds)       # ai.move: the commands of the walk go after the pack
    trebuchet.tick(g, dt)            # gather.Gather.step: dt AoE2 seconds of packing and unpacking
"""
import math

import units

NAME = "TREBUCHET"
PACK = 11.1                 # AoE2 seconds to pack or to unpack
MARGIN = 0.5                # blocks: it unpacks this far inside its range, so that the plugin can shoot
UNPACKED = (1, 150)         # melee and pierce armor unpacked (AoE2 DE wiki); packed: combat.STATS


def state(g, u):
    """"packed", "walking" (packed, to the range of a target), "unpacking", "unpacked" or "packing"."""
    return vars(g).setdefault("trebs", {}).get(u, ["packed"])[0]


def pack_time(g):
    """The AoE2 seconds to pack or unpack: PACK times the factor of the technologies (Kataparuto: 0.25, #4275)."""
    import train                                                   # train imports gather, gather imports this module
    return PACK * math.prod(train.value("pack_time", t, 1) for t in g.techs)


def stats(g, u):
    """The combat values of trebuchet u with the technologies of the player (train.stats) and the armor of its state:
    packed (also while it unpacks) the armor of combat.STATS, unpacked (also while it packs) UNPACKED and the class ram."""
    import combat                                                  # combat imports gather, gather imports this module
    import train
    s, base = train.stats(g, NAME, u), combat.stats(NAME)
    if state(g, u) in ("unpacked", "packing"):
        s = s._replace(melee=s.melee - base.melee + UNPACKED[0], pierce=s.pierce - base.pierce + UNPACKED[1],
                       classes=(*s.classes, combat.RAM))           # only unpacked in the class "Rams" (#1402)
    return s


def stats_command(g, u):
    """The `aoe stats` command of trebuchet u in its state (#1409)."""
    import civs, combat
    return combat.stats_command(u, NAME, stats(g, u), civs.taken(g, NAME), civs.friendly(g, NAME))


def scale_command(u, packed):
    """The size of the crew mob of trebuchet u: smaller packed, as in the table of decision #1525 (#1664)."""
    s = units.siege_scale(NAME + "_PACKED" * packed)
    return f"execute as {u} on passengers run attribute @s minecraft:scale base set {s:g}"


def range_command(g, u, blocks=None):
    """The `aoe range` command of trebuchet u: its AoE2 range (with the technologies of the player), or blocks."""
    import combat                                                  # combat imports gather, gather imports this module
    import train
    cmd = combat.range_command(u, NAME, g.map.T, s=train.stats(g, NAME)).split()
    return " ".join(cmd[:3] + [str(cmd[3] if blocks is None else blocks)] + cmd[4:])


def gap(g, u, target):
    """(blocks from trebuchet u to the edge of its range around target, the place to walk to): more than 0 is out of
    range. A building target (g.forts) counts from the nearest point of its box. None when a position is unknown."""
    p = g.pos(u)
    if target in vars(g).get("forts", {}):
        x0, y0, z0, x1, _, z1 = g.forts[target]
        to = ((x0 + x1 + 1) / 2, y0, (z0 + z1 + 1) / 2)
        d = math.hypot(max(0, x0 - p[0], p[0] - x1 - 1), max(0, z0 - p[2], p[2] - z1 - 1)) if p else None
    else:
        to = g.pos(target)
        d = p and to and math.hypot(to[0] - p[0], to[2] - p[2])
    if d is None:
        return None
    import train                                                   # train imports gather, gather imports this module
    return d - (train.stats(g, NAME).range * g.map.T - MARGIN), to


def walk(g, u, target, to):
    """The packed trebuchet u walks toward place to of target, at its walk speed."""
    import ai                                                      # ai imports this module
    import gather
    import train
    g.command(ai.speed_command(u, NAME, g.map.T, gather.NORMAL * train.speed(g, NAME, u)))
    g.command(f"aoe moveto {u} {to[0]} {to[1]} {to[2]}")
    g.trebs[u] = ["walking", 0.0, [target, to]]


def unpack(g, u, target):
    """The trebuchet u stops, unpacks and then attacks the entity target. Unpacked: it attacks at once. A target out
    of range: it walks packed until the target is in range (unpacked, it packs first)."""
    then = [f"aoe attack {u} {target}"]                            # the range goes first, at the end of the unpack
    far = state(g, u) in ("packed", "walking", "unpacked") and gap(g, u, target)
    if far and far[0] > 0:
        if state(g, u) == "unpacked":
            return move(g, u, [("walk", target)])
        return walk(g, u, target, far[1])
    if state(g, u) == "unpacked":
        for c in [range_command(g, u), *then]:
            g.command(c)
        return
    if state(g, u) != "unpacking":                                 # packed or packing: AoE2 cancels the pack at once
        g.command(f"aoe stop {u}")
        g.command(f"aoe speed {u} 0")
    g.trebs[u] = ["unpacking", pack_time(g) if state(g, u) != "unpacking" else g.trebs[u][1], then]


def move(g, u, cmds):
    """The trebuchet u packs and then sends cmds (the walk speed and the walk). Packed: it walks at once."""
    if state(g, u) == "walking":                                   # a new order: no more walk to a target
        g.trebs[u] = ["packed", 0.0, []]
    if state(g, u) == "packed":
        for c in cmds:
            g.command(c)
        return
    if state(g, u) != "packing":
        g.command(f"aoe stop {u}")
        g.command(range_command(g, u, 0))
    g.trebs[u] = ["packing", pack_time(g) if state(g, u) != "packing" else g.trebs[u][1], cmds]


def tick(g, dt):
    """dt AoE2 seconds: an own trebuchet that the program does not know yet is packed (range 0); a pack or an unpack
    that is done sends its commands."""
    trebs = vars(g).setdefault("trebs", {})
    for u in sorted(u for u, n in g.soldiers.items() if n == NAME and u not in trebs):
        g.command(scale_command(u, True))                          # a TREBUCHET of the map has the unpacked size
        g.command(range_command(g, u, 0))
        trebs[u] = ["packed", 0.0, []]
    for u in sorted(trebs):
        if u not in g.soldiers:                                    # dead or converted
            del trebs[u]
            continue
        st, left, then = trebs[u]
        if st == "walking":                                        # unpack in range, or walk on to a moved target
            far = gap(g, u, then[0])
            if far is None:                                        # the target is gone
                g.command(f"aoe stop {u}")
                trebs[u] = ["packed", 0.0, []]
            elif far[0] <= 0:
                trebs[u] = ["packed", 0.0, []]
                unpack(g, u, then[0])
            elif math.dist(far[1], then[1]) > 2:
                walk(g, u, then[0], far[1])
            continue
        if st not in ("packing", "unpacking"):
            continue
        if left - dt > 0:
            trebs[u][1] = left - dt
            continue
        trebs[u] = ["packed" if st == "packing" else "unpacked", 0.0, []]
        g.command(scale_command(u, st == "packing"))               # the size and the armor of the new state
        g.command(stats_command(g, u))
        if st == "unpacking":                                      # the range of now: a research during the unpack (#1414)
            g.command(range_command(g, u))
        for c in then:
            _ = unpack(g, u, c[1]) if isinstance(c, tuple) else g.command(c)   # ("walk", target): to its range
