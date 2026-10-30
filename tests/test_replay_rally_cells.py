"""Live replay: the units that a building trains to one gather point on the ground get one free cell each next to it
(#2880), so that the collision of the entities does not push them off their replay positions. Fake clock and RCON."""
import math

import pytest
from test_replay_rally import play, point
from test_replay_spawn import queue


@pytest.mark.parametrize("ai", [False, True])
def test_four_units_of_one_gather_point_stand_on_four_cells_near_it(ai):
    r = play([point(target=None, tile=(12.5, 12.5)), queue(amount=4)], 300000, ai)
    cells = [v.cell for i, v in sorted(r.units.items()) if i < 0]
    assert len(cells) == 4 and len(set(cells)) == 4
    assert all(math.dist(c, (50, 50)) <= 2 for c in cells)            # T = 4: within half a tile of the point
    assert (50, 50) in cells                                           # the first unit stands on the point
