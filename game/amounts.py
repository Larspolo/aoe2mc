"""The resources left above a partially drained resource (#3284, owner decision B of #3275): a tree, a fruit bush, a
mine, a farm or a carcass that a villager took from shows its whole amount in a `text_display` (billboard "center", as
the rally point of train.py): no plugin and no world change. A full resource shows nothing, an empty one loses its
display. Gather.step calls tick()."""
import gather

TAG = "aoe_left"
HIGH = {"trees": 7, "bushes": 2, "mines": 3, "farms": 1, "carcasses": 2}   # blocks above the ground of the tile


def full(g):
    """{(kind, tile): the full amount} of the resources whose full amount the map does not hold: the mines of
    aoe2mc.json (MINES) and the fruit bushes (BUSH_FOOD). Kept on g: a load reads the same objects."""
    if "left_full" not in vars(g):
        out = {}
        for o in g.data.get("objects", ()):
            if o["kind"] == "other" and o["name"] in gather.MINES:
                out["mines", (int(o["tile"][0]), int(o["tile"][1]))] = gather.MINES[o["name"]][1]
        g.left_full = out
    return g.left_full


def drained(g):
    """{(kind, tile): whole amount} of the partially drained resources of the map of g."""
    m, fulls = g.map, full(g)
    out = {("trees", t): a for t, a in m.trees.items() if 0 < a < gather.TREE_WOOD}
    out |= {("bushes", t): a for t, a in m.bushes.items() if 0 < a < gather.BUSH_FOOD}
    out |= {("mines", t): a for r in m.mines.values() for t, a in r.items() if 0 < a < fulls.get(("mines", t), 0)}
    out |= {("farms", t): a for t, a in m.farms.items() if 0 < a < m.farm_food}
    out |= {("carcasses", t): a for t, a in m.carcasses.items() if a > 0}   # it rots from the kill: never full
    return {k: int(a) for k, a in out.items() if int(a) > 0}


def tick(g):
    """Show the new whole amounts, and kill the displays of the full or empty resources. No command while nothing
    changed."""
    if not hasattr(g, "map") or not hasattr(g, "data") or vars(g).get("share") is not None:   # a bot shows nothing
        return
    shown = vars(g).get("left_shown")
    if shown is None:                                                  # a new or a loaded game: no old display
        g.command(f"kill @e[type=text_display,tag={TAG}]")
        shown = g.left_shown = {}
    now = drained(g)
    for key in [k for k in shown if k not in now]:
        g.command(f"kill @e[type=text_display,tag={tag(key)}]")
        del shown[key]
    for key, n in sorted(now.items()):
        if shown.get(key) == n:
            continue
        if key in shown:
            g.command(f'data merge entity @e[type=text_display,tag={tag(key)},limit=1] {{text:"{n}"}}')
        else:
            x, y, z = spot(g, key)
            g.command(f"kill @e[type=text_display,tag={tag(key)}]")    # one display per tile with more people
            g.command(f'summon text_display {x} {y} {z} {{text:"{n}",billboard:"center",Tags:["{TAG}","{tag(key)}"]}}')
        shown[key] = n


def tag(key):
    kind, (x, z) = key
    return f"{TAG}.{kind}.{x}.{z}"


def spot(g, key):
    """The block position of the display: above the middle of the tile."""
    kind, (tx, tz) = key
    T = g.map.T
    x, z = tx * T + T // 2, tz * T + T // 2
    y = g.map.y(x, z)
    return x + 0.5, (0 if y is None else y) + HIGH[kind], z + 0.5
