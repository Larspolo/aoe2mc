"""A felled tree on a slope lies on the ground of its footprint, not in the ground of the hill (#1124)."""
import re

from game import gather

TAGS = {"#minecraft:logs": lambda b: b.endswith("_log"), "#minecraft:leaves": lambda b: b.endswith("_leaves"),
        "#minecraft:replaceable": lambda b: b in ("minecraft:air", "minecraft:short_grass")}


class World:
    """A fake server that runs the fill, setblock and execute if/unless block commands of Gather on a block dict."""

    def __init__(self, blocks):
        self.blocks, self.log = blocks, []

    def get(self, x, y, z):
        return self.blocks.get((x, y, z), "minecraft:air").split("[")[0]

    def match(self, b, f):
        return TAGS.get(f, lambda b: False)(b) if f.startswith("#") else b == f.split("[")[0]

    def command(self, cmd):
        self.log.append(cmd)
        while m := re.match(r"execute (if|unless) block (\S+) (\S+) (\S+) (\S+) ", cmd):
            if (m[1] == "if") != self.match(self.get(*map(int, m.groups()[1:4])), m[5]):
                return ""
            cmd = "execute " + cmd[m.end():]
        cmd = cmd.removeprefix("execute run ")
        if m := re.fullmatch(r"setblock (\S+) (\S+) (\S+) (\S+)", cmd):
            self.blocks[tuple(map(int, m.groups()[:3]))] = m[4]
        elif m := re.fullmatch(r"fill (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+)(?: (replace|keep) ?(\S+)?)?", cmd):
            x0, y0, z0, x1, y1, z1 = map(int, m.groups()[:6])
            for x in range(x0, x1 + 1):
                for y in range(y0, y1 + 1):
                    for z in range(z0, z1 + 1):
                        old = self.get(x, y, z)
                        if m[8] == "keep" and old != "minecraft:air" or m[9] and not self.match(old, m[9]):
                            continue
                        self.blocks[(x, y, z)] = m[7] if ":" in m[7] else "minecraft:" + m[7]
        return ""


def tree_world(top):
    """An oak at tile (5, 6) (footprint x 20-23, z 24-27, tile size 4) on ground with height top(x) and the barriers
    of the converter; aoe2mc.json "ground" over the footprint is the barrier top."""
    blocks = {}
    for x in range(14, 30):
        for z in range(18, 34):
            for y in range(top(x) - 3, top(x) + 1):
                blocks[(x, y, z)] = "minecraft:dirt"
            if 20 <= x < 24 and 24 <= z < 28:
                for y in range(top(x) + 1 + (x == 21 and z == 25), top(x) + 4):
                    blocks[(x, y, z)] = "minecraft:barrier"
    blocks[(21, top(21) + 1, 25)] = "minecraft:red_mushroom"            # a plant in the trunk row
    for y in range(top(22) + 1, top(22) + 7):
        blocks[(22, y, 26)] = "minecraft:oak_log[axis=y]"
    for x in range(20, 24):
        for z in range(24, 28):
            blocks[(x, top(22) + 6, z)] = "minecraft:oak_leaves[persistent=true]"
    m = {"tile_size": 4, "objects": [{"kind": "other", "name": "TREE_OAK", "tile": [5.5, 6.5]}],
         "ground": [" ".join(str(top(x) + (4 if 20 <= x < 24 and 24 <= z < 28 else 1)) for x in range(48))
                    for z in range(48)]}
    world = World(blocks)
    return world, gather.Gather(world, m, start={})


FULL = gather.TREE_WOOD - 1                                            # the wood of a tree after the first chop


def chop(g, wood):
    g.map.trees[(5, 6)] = wood
    g.trunk((5, 6)) if wood else g.fell((5, 6))


def row(world, top):
    """The trunk row z = 25: the block at the footprint ground + 1 of each column, and any log above it."""
    return [world.get(x, top(x) + 1, 25) for x in range(20, 24)], \
        [(x, y) for x in range(20, 24) for y in range(top(x) + 2, top(x) + 12) if world.get(x, y, 25).endswith("_log")]


def test_the_trunk_of_a_tree_on_a_slope_lies_on_the_ground_of_its_footprint():
    top = lambda x: 40 + x                                          # noqa: E731, a slope of 1 block per block
    world, g = tree_world(top)
    chop(g, FULL)
    assert row(world, top) == (["minecraft:oak_log"] * 4, [])          # each log on the ground of its column
    assert world.blocks[(20, top(20) + 1, 25)] == "minecraft:oak_log[axis=x]"
    assert world.get(20, top(20) + 2, 25) == "minecraft:oak_leaves"     # the crown on the tip
    assert world.get(22, top(22), 26) == "minecraft:spruce_log" and world.get(22, top(22) + 1, 26) == "minecraft:air"
    chop(g, gather.TREE_WOOD // 2)
    assert row(world, top) == (["minecraft:barrier"] * 2 + ["minecraft:oak_log"] * 2, [])
    assert world.get(22, top(22) + 2, 25) == "minecraft:oak_leaves" and world.get(20, top(20) + 2, 25) != "minecraft:oak_leaves"
    chop(g, 0)
    assert row(world, top) == (["minecraft:air"] * 4, [])
    assert world.get(22, top(22), 26) == "minecraft:spruce_log" and world.get(22, top(22) + 1, 26) == "minecraft:air"
    assert not [k for k, b in world.blocks.items() if b == "minecraft:barrier"]


def test_the_trunk_of_a_tree_on_flat_ground_is_as_before():
    top = lambda x: 63                                              # noqa: E731
    world, g = tree_world(top)
    chop(g, FULL)
    assert row(world, top) == (["minecraft:oak_log", "minecraft:red_mushroom"] + ["minecraft:oak_log"] * 2, [])   # as before
    assert not [c for c in world.log if c.startswith("execute")]      # no probe: the same commands as before
    assert world.get(22, 63, 26) == "minecraft:spruce_log"
