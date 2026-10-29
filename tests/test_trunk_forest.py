"""A felled tree in a forest on a hill lies on the ground of its footprint: the other trees block the cells next to it,
and the one free cell is at the foot of the hill (#1157)."""
from test_trunk_slope import FULL, chop, row, tree_world


def test_the_trunk_of_a_tree_in_a_forest_on_a_hill_lies_on_the_ground_of_its_footprint():
    top = lambda x: 40 + x                                          # noqa: E731, a slope of 1 block per block
    world, g = tree_world(top)
    feet = {(x, z) for x in range(20, 24) for z in range(24, 28)}
    g.map.blocked |= g.map.around(feet) - {(19, 23)}                  # the other trees; one free cell at the foot
    assert {g.map.y(x, z) for x, z in g.map.around(feet)} == {top(19) + 1}
    chop(g, FULL)
    assert row(world, top) == (["minecraft:oak_log"] * 4, [])          # each log on the ground of its column
    assert world.get(22, top(22), 26) == "minecraft:spruce_log" and world.get(22, top(22) + 1, 26) == "minecraft:air"
    chop(g, 0)
    assert row(world, top) == (["minecraft:air"] * 4, [])
    assert not [k for k, b in world.blocks.items() if b == "minecraft:barrier"]
