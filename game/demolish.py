"""
Delete an own building or construction site from its menu, as the Delete button of AoE2 (#3452, epic #3450). Each
menu of an own building has the item ITEM in its last slot (the Delete button is at the bottom right of the AoE2
command panel): the menu of a training building (train.show), of a market (market.show), of a building with units
inside (garrison.open_menu), and the menu of open_menu() for an own building or site with no other menu (a house, a
tower, a wall).

A complete building falls as at 0 hit points: `aoe destroy` of its target entity (the plugin fills its box with air),
then ruins.fall (the queue gives its cost back, the units inside come out) and Gather.free (the footprint and the
minimap). Vanilla has no plugin, so only Paper shows the item for a complete building.
An unfinished construction site goes at once: its blocks become air, its cells are free, its builders stop. The AoE2
rule of the refund (docs/research/gameplay.md, "Delete"): a foundation that nobody started to build gives back its
full cost, a started one gives back nothing.
Never a building of another player or of Gaia: the footprints come from ruins.own and the sites of the player.

    demolish.open_menu(g, player, cell)   # gather.Gather.click: an own building or site with no other menu
"""
ITEM = (53, "tnt", "Delete", "Click: the building falls")   # the last slot of the menu, as the AoE2 button


def site(g, rect):
    """The unfinished own construction site with block footprint rect (x0, x1, z0, z1), or None."""
    return next((s for s in g.sites if s.get("player", g.player) == g.player and s.get("progress", 1) < 1 and not s.get("done")
                 and tuple(s["footprint"]) == tuple(rect)), None)


def shown(g, rect):
    """True when the menu of the own building or site rect has the item Delete."""
    import ruins                                                   # ruins -> gather -> this module
    return site(g, rect) is not None or getattr(g, "paper", False) and tuple(rect) in ruins.own(g).values()


def at(g, cell):
    """The block footprint of the own building or unfinished site with the block cell (x, z) in it, or None."""
    import ruins
    rects = [*ruins.own(g).values(), *(tuple(s["footprint"]) for s in g.sites
                                       if s.get("player", g.player) == g.player and s.get("progress", 1) < 1 and not s.get("done"))]
    return next((r for r in rects if cell and r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]), None)


def name(g, rect):
    """The AoE2 name of the own building or site rect."""
    x0, x1, z0, z1 = rect
    return next((o["name"] for o in g.data["objects"] if o["kind"] == "building" and list(o.get("footprint", ())) == [x0, z0, x1, z1]),
                None) or next(s["name"] for s in g.sites if tuple(s["footprint"]) == rect)


def open_menu(g, player, cell):
    """Open the menu with only the item Delete of the own building or site at the block cell (x, z). Returns its
    footprint, or None."""
    import build, menu
    rect = at(g, cell)
    if rect is None or not shown(g, rect):
        return None
    menu.show(g, player, build.pretty(name(g, rect)), [ITEM], lambda p, slot, shift: slot == ITEM[0] and delete(g, p, rect))
    return rect


def delete(g, player, rect):
    """Delete the own building or site rect (the item Delete of its menu) and close the menu. Returns True."""
    import menu
    rect = tuple(rect)
    if (s := site(g, rect)) is not None:
        unfound(g, s)
    elif shown(g, rect):
        fall(g, rect)
    else:
        return False
    menu.close(g, player)
    return True


def fall(g, rect):
    """The complete own building rect falls as at 0 hit points: the plugin removes its target and its blocks."""
    import combat, ruins
    x0, x1, z0, z1 = rect
    uuid = combat.target_uuid([x0, z0, x1, z1])
    g.command(f"aoe destroy {uuid}")
    vars(g).get("ruins_seen", set()).discard(uuid)                 # ruins.tick does not let it fall a second time
    ruins.fall(g, rect)
    g.free(uuid)


def unfound(g, s):
    """Remove the unfinished site s: the refund of AoE2, air in its box (the water under a dock or a fish trap comes
    back), free cells, and its builders stop."""
    import build, combat, fleet
    if s["progress"] == 0:
        for r, v in s.get("paid", build.price(g, s["name"])).items():
            g.stock[r] += v
            g.command(f"scoreboard players add {r.capitalize()} {g.board} {v}")
    g.sites = [t for t in g.sites if t is not s]
    x0, x1, z0, z1 = s["footprint"]
    bx0, y0, bz0, bx1, y1, bz1 = combat.building_box({"footprint": [x0, z0, x1, z1]}, g.map.ground)
    y0 = max(y0, int(fleet.level(g)) + 1)                         # above the water, as cheats.ruin
    g.command(f"fill {bx0} {y0} {bz0} {bx1} {y1} {bz1} minecraft:air")
    for c, state in sorted(s.get("under", {}).items()):
        if state == "minecraft:water":
            g.command("setblock {} {} {} minecraft:water".format(*c))
    for m in {id(h.map): h.map for h in [g, *build.sides(g)]}.values():
        m.blocked -= {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    if getattr(g, "paper", False):
        g.command(f"aoe minimap unbuild {x0} {z0}")
    for v in [*g.villagers.values(), *vars(g).get("ships", {}).values()]:
        if v.site is s:
            v.site = None
            if v.uuid in g.villagers:
                g.set(v, "idle")
            else:
                v.state = "idle"
    g.command("playsound minecraft:block.wood.break master @a[team=p{}] {} ~ {} 1 1".format(
        g.player, (x0 + x1) / 2, (z0 + z1) / 2))
