"""An empty fruit bush frees its tile in the gather game, as an empty tree or mine does (#602)."""
from test_gather_food import food_map

from game import gather


def test_an_empty_bush_frees_its_tile():
    server, g = food_map()
    cells = g.map.cells((10, 10))
    assert cells <= g.map.blocked
    g.select("v")
    g.send((10, 10))
    for _ in range(3000):
        g.step()
        if g.map.bushes[(10, 10)] == 0:
            break
    assert g.map.bushes[(10, 10)] == 0
    assert not cells & g.map.blocked and all(g.map.free(x, z) for x, z in cells)
    clear = [c for c in server.log if c.startswith("fill 10 ") and c.endswith("air replace minecraft:barrier")]
    assert len(clear) == 1
    dead = [c for c in server.log if "minecraft:dead_bush replace" in c]
    assert dead and server.log.index(dead[0]) < server.log.index(clear[0])    # the dead bush stays as the look


def test_a_bush_with_food_still_blocks():
    server, g = food_map()
    g.select("v")
    g.send((10, 10))
    for _ in range(3000):
        g.step()
        if g.map.bushes[(10, 10)] < gather.BUSH_FOOD // 2:
            break
    assert g.map.cells((10, 10)) <= g.map.blocked
    assert not any(c.endswith("air replace minecraft:barrier") for c in server.log if c.startswith("fill 10 "))
