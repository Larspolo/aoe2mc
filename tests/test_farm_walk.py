"""game/gather.py: a farmer walks over its farm while it works, as in AoE2 (#591)."""
import math

from test_gather_farms import farm_map


def test_a_farmer_works_on_its_farm_and_moves_to_another_farm_cell_per_food():
    server, g = farm_map()
    v = g.villagers["v"]
    g.selected = {"v"}
    g.send((10, 10))
    spot = g.map.spot((10, 10))
    assert g.goals((10, 10)) == spot and v.path[-1] in spot                # the goals are cells inside the farm
    while v.state != "chop":
        g.step()
    cells, walked = [v.cell], v.walked
    while v.state == "chop":
        g.step()                                                         # the walk to the mill starts a tick later
        if v.cell != cells[-1]:
            cells.append(v.cell)
    assert v.load == g.carry and len(cells) == g.carry + 1               # one farm cell further per food
    assert set(cells) <= spot and len(set(cells)) > 3
    assert all(math.dist(a, b) < 1.5 for a, b in zip(cells, cells[1:]))  # a step to a next cell, no jump
    assert v.walked == walked                                            # work, not a walk (measure_gather.py)
    assert any(c.startswith("tp v ") for c in server.log)


def test_the_farm_walk_turns_at_the_end_of_the_farm():
    _, g = farm_map()
    v = g.villagers["v"]
    g.selected = {"v"}
    g.send((10, 10))
    while v.state != "chop":
        g.step()
    seen = []
    for _ in range(2 * len(g.map.spot((10, 10))) + 2):
        g.tend(v)
        seen.append(v.cell)
    assert set(seen) == g.map.spot((10, 10))                            # all cells of the farm
    assert all(math.dist(a, b) < 1.5 for a, b in zip(seen, seen[1:]))
