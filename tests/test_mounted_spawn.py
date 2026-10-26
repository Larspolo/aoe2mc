"""A mounted unit spawns one cell away from the walls of its building (#767): the rider sits about 0.7 blocks behind
the middle of its horse, so on a cell next to the building its head is in the wall and it suffocates."""
from test_gather import grid

from game import gather

STABLE = (10, 13, 2, 5)                                               # block footprint x0, x1, z0, z1


def game_map(extra=()):
    objects = [{"kind": "building", "name": "STABLE", "player": 1, "tile": [11.5, 3.5], "footprint": [10, 2, 13, 5]},
               *extra]
    return gather.Gather(None, grid([[64] * 24 for _ in range(24)], objects)).map


def test_a_foot_unit_spawns_next_to_the_building():
    assert game_map().front(STABLE)[0] == (11, 5)


def test_a_mounted_unit_has_free_cells_on_all_sides():
    m = game_map()
    cells = m.front(STABLE, mounted=True)
    assert cells[0] == (11, 6)                                        # south, in the middle, one cell out
    for x, z in cells:
        assert all(m.free(x + dx, z + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)), (x, z)
        assert not (STABLE[0] - 1 <= x <= STABLE[1] and STABLE[2] - 1 <= z <= STABLE[3])   # not next to a wall


def test_a_mounted_unit_skips_a_cell_next_to_another_building():
    house = {"kind": "building", "name": "HOUSE", "player": 1, "tile": [11, 8], "footprint": [10, 7, 12, 9]}
    cells = game_map([house]).front(STABLE, mounted=True)
    assert (11, 6) not in cells and (10, 6) not in cells and cells
