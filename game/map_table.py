"""
The map table (#2586, part of #2580; owner decision #2585: option A). Each player gets a cartography table near the
own town center with an item frame on it that shows map 0 (the minimap of the converter, #838, with the units of the
plugin, #2581). A right click with the command stick on a pixel of the framed map sends the selected units to that
place, as a right click on the AoE2 minimap: the move order of a click on the ground (Gather.walk_to, #1368).
The plugin (MapTable.java) reads the click position on the frame and sets the block of the pixel in the scores X and
Z of the player, then CLICK to 1: vanilla has no event for the position of a click on an entity. Only on Paper.
"""
import json
import re

CLICK, X, Z = "aoe_map", "aoe_map_x", "aoe_map_z"          # the scores of MapTable.java
TAG = "aoe2mc.map_table"


def cell(g):
    """The block cell of the table: the free cell at the east end of the south side of the own town center (the
    spawn cells of the town center are in the middle, Gather.front), or None without a town center or a free cell."""
    tc = next((o for o in g.data["objects"] if o["kind"] == "building" and o["name"] == "TOWN_CENTER"
               and o["player"] == g.player), None)
    if tc is None:
        return None
    x0, z0, x1, z1 = tc["footprint"]
    ring = g.map.around({(x, z) for x in range(x0, x1) for z in range(z0, z1)})
    return max(ring, key=lambda c: (c[1] == z1, c[0]), default=None)


def setup(g):
    """Put the table and its framed map (fixed: no turn and no drop) and make the scores of the clicks."""
    for o in (CLICK, X, Z):
        g.command(f"scoreboard objectives add {o} dummy")
    if (c := cell(g)) is None:
        return
    x, z = c
    y = g.map.y(x, z)
    g.map.blocked.add(c)
    tag = f"{TAG}.p{g.player}"
    item = {"id": "minecraft:filled_map", "count": 1, "components": {"minecraft:map_id": 0}}
    g.command(f"kill @e[type=minecraft:glow_item_frame,tag={tag}]")    # a loaded game: one table
    g.command(f"setblock {x} {y} {z} minecraft:cartography_table")
    # Pos in the tag: summon reads the tag before it moves the entity, so without Pos the frame is at 0 0 0, more
    # than 16 blocks from block_pos, and Minecraft logs "Block-attached entity at invalid position" (#3262)
    g.command(f"summon minecraft:glow_item_frame {x} {y + 1} {z} {{Facing:1b,Fixed:1b,Invulnerable:1b,"
              f"Pos:[{x + 0.5}d,{y + 1.0}d,{z + 0.5}d],"
              f'block_pos:[I;{x},{y + 1},{z}],Tags:["{TAG}","{tag}"],Item:{json.dumps(item)}}}')


def score(g, name, objective):
    m = re.search(r" has (-?\d+)", g.command(f"scoreboard players get {name} {objective}"))
    return int(m[1]) if m else None


def tick(g):
    """Send the selection of each player that clicked the framed map to the block of the pixel. With no selection,
    move the view there, as a click on the AoE2 minimap: the player is the camera, so a tp to the ground that keeps
    the yaw and pitch, the form of the trigger effect "Change View" (#2610, #2788)."""
    if not getattr(g, "paper", False):
        return
    who = g.who
    sel = who[:-1] + f",scores={{{CLICK}=1..}}]" if who.endswith("]") else who + f"[scores={{{CLICK}=1..}}]"
    if "passed" not in g.command(f"execute if entity {sel}"):
        return
    for name in g.people():
        if not name or not score(g, name, CLICK):
            continue
        g.command(f"scoreboard players reset {name} {CLICK}")
        x, z = score(g, name, X), score(g, name, Z)
        if x is None or z is None:
            continue
        if g.selected:
            g.walk_to(name, (x, z))
        elif (y := g.map.y(x, z)) is not None:
            g.command(f"tp {name} {x + 0.5} {y} {z + 0.5}")
