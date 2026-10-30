"""game/gather.py: fell frees the cells of an empty tree when the ground next to it differs by at most 1 block, so a
walker crosses the stump (#4063). In de-64.3 the cells of cut trees on such a step stayed blocked, shut four
lumberjacks in and gave 26 idle minutes. A steeper hill keeps the cells blocked."""
from test_gather import FakeServer, grid

from game import gather

TREE = (5, 6)                                                          # footprint x 20..23, z 24..27


def game(west):
    data = grid([[64] * 48 for _ in range(48)], [{"kind": "other", "name": "TREE_OAK", "tile": [5.5, 6.5]}])
    data.update(tile_size=4, level_height=3)
    data["ground"] = [" ".join("70" if 20 <= x < 24 and 24 <= z < 28 else str(west) if x < 20 else "64"
                               for x in range(48)) for z in range(48)]
    data["players"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}
    g = gather.Gather(FakeServer({"Steve": {"Pos": (9.5, 64.0, 9.5)}}), data, start={}).setup()
    g.map.blocked |= {(x, z) for x in range(20, 24) for z in range(24, 28)}   # the barriers of the converter
    return g


def test_a_step_of_one_block_frees_the_stump_at_the_lower_ground():
    g = game(65)
    g.fell(TREE)
    assert all(g.map.free(x, z) and g.map.y(x, z) == 64 for x in range(20, 24) for z in range(24, 28))
    assert g.map.path((19, 25), {(24, 25)})                            # across the stump


def test_a_hill_keeps_the_stump_blocked():
    g = game(67)
    g.fell(TREE)
    assert not any(g.map.free(x, z) for x in range(20, 24) for z in range(24, 28))
