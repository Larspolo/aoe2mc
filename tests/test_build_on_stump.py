"""game/build.py: a player places a building on the spot of a chopped tree, as in AoE2 (#3265, owner feedback in a
demo). fell frees the cells of the footprint (its barriers go) at the ground of the stump; a standing tree still blocks."""
from test_gather import FakeServer, grid

from game import build, gather

TREE = (5, 6)                                                          # footprint x 20..23, z 24..27


def game():
    data = grid([[64] * 48 for _ in range(48)], [{"kind": "other", "name": "TREE_OAK", "tile": [5.5, 6.5]}])
    data.update(tile_size=4, level_height=3)
    data["ground"] = [" ".join("67" if 20 <= x < 24 and 24 <= z < 28 else "64" for x in range(48)) for z in range(48)]
    data["players"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}
    server = FakeServer({"Steve": {"Pos": (9.5, 64.0, 9.5)}})
    g = gather.Gather(server, data, start={}).setup()
    g.stock.update(food=1000, wood=1000, stone=1000, gold=1000)
    g.map.blocked |= {(x, z) for x in range(20, 24) for z in range(24, 28)}   # the barriers of the converter
    return server, g


def placed(g, name, cell):
    g.map.pick_ground = lambda eye, d: cell
    return build.place(g, "Steve", name, (0, 70, 0), (0, -1, 0))


def test_a_standing_tree_refuses_a_farm():
    _, g = game()
    assert placed(g, "FARM", (21, 25)) is None


def test_a_farm_goes_on_a_chopped_tree():
    _, g = game()
    g.fell(TREE)
    assert all(g.map.free(x, z) and g.map.y(x, z) == 64 for x in range(20, 24) for z in range(24, 28))
    assert placed(g, "FARM", (21, 25))


def test_a_unit_still_refuses_the_spot():
    _, g = game()
    g.fell(TREE)
    g.map.blocked.add((21, 25))                                        # another blocker on the stump
    assert placed(g, "FARM", (21, 25)) is None
