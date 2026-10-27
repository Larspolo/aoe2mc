"""The trebuchet in the game program (#1351, epic #1348): it packs and unpacks as in AoE2 DE (AoE2 wiki "Trebuchet":
"Cannot attack when packed. Cannot move when unpacked. Takes 11.1 seconds to pack and unpack."). An attack order
unpacks it: it stops at once and shoots after PACK AoE2 seconds. A move order packs it: it walks after PACK seconds.
A new trebuchet, and one of the map, is packed.

Minecraft feature: the trebuchet stays the same minecart on its carrier (#836). Unpacked: movement_speed 0 on the
carrier (`aoe speed`) and its AoE2 range (`aoe range`, combat.range_command); packed: the walk speed and range 0, so
the plugin lets it shoot nothing.

    trebuchet.unpack(g, u, target)   # gather.Gather.attack: the trebuchet u attacks target after the unpack
    trebuchet.move(g, u, cmds)       # ai.move: the commands of the walk go after the pack
    trebuchet.tick(g, dt)            # gather.Gather.step: dt AoE2 seconds of packing and unpacking
"""
NAME = "TREBUCHET"
PACK = 11.1                 # AoE2 seconds to pack or to unpack


def state(g, u):
    """"packed", "unpacking", "unpacked" or "packing"."""
    return vars(g).setdefault("trebs", {}).get(u, ["packed"])[0]


def range_command(g, u, blocks=None):
    """The `aoe range` command of trebuchet u: its AoE2 range (with the technologies of the player), or blocks."""
    import combat                                                  # combat imports gather, gather imports this module
    import train
    cmd = combat.range_command(u, NAME, g.map.T, s=train.stats(g, NAME)).split()
    return " ".join(cmd[:3] + [str(cmd[3] if blocks is None else blocks)] + cmd[4:])


def unpack(g, u, target):
    """The trebuchet u stops, unpacks and then attacks the entity target. Unpacked: it attacks at once."""
    then = [range_command(g, u), f"aoe attack {u} {target}"]
    if state(g, u) == "unpacked":
        for c in then:
            g.command(c)
        return
    if state(g, u) != "unpacking":                                 # packed or packing: AoE2 cancels the pack at once
        g.command(f"aoe stop {u}")
        g.command(f"aoe speed {u} 0")
    g.trebs[u] = ["unpacking", PACK if state(g, u) != "unpacking" else g.trebs[u][1], then]


def move(g, u, cmds):
    """The trebuchet u packs and then sends cmds (the walk speed and the walk). Packed: it walks at once."""
    if state(g, u) == "packed":
        for c in cmds:
            g.command(c)
        return
    if state(g, u) != "packing":
        g.command(f"aoe stop {u}")
        g.command(range_command(g, u, 0))
    g.trebs[u] = ["packing", PACK if state(g, u) != "packing" else g.trebs[u][1], cmds]


def tick(g, dt):
    """dt AoE2 seconds: an own trebuchet that the program does not know yet is packed (range 0); a pack or an unpack
    that is done sends its commands."""
    trebs = vars(g).setdefault("trebs", {})
    for u in sorted(u for u, n in g.soldiers.items() if n == NAME and u not in trebs):
        g.command(range_command(g, u, 0))
        trebs[u] = ["packed", 0.0, []]
    for u in sorted(trebs):
        if u not in g.soldiers:                                    # dead or converted
            del trebs[u]
            continue
        st, left, then = trebs[u]
        if st not in ("packing", "unpacking"):
            continue
        if left - dt > 0:
            trebs[u][1] = left - dt
            continue
        trebs[u] = ["packed" if st == "packing" else "unpacked", 0.0, []]
        for c in then:
            g.command(c)
