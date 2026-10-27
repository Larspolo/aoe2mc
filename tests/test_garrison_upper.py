"""The garrison of a town center stands on the floor of its hall, where the player sees it (#2054)."""
import pytest
from test_town_center_pass import town_center

import aoe2mc
import buildings


@pytest.mark.parametrize("arch", sorted(buildings.ARCH))
def test_the_garrison_cells_of_a_town_center_are_in_its_hall(arch):
    buildings.INSIDE.clear()
    cols, o, last = town_center(arch, ref=7)
    x0, z0, x1, z1 = o["footprint"]
    base = int(cols.wtop[x0:x1, z0:z1].max())
    cells, y, _ = buildings.INSIDE[7]

    def state(x, y, z):
        return aoe2mc.B.states[last[(x, y, z)]] if (x, y, z) in last else "minecraft:air"
    assert y > base + 3                                                  # above the open ground floor
    assert len(cells) >= 5
    for x, z in cells:
        assert x0 <= x < x1 and z0 <= z < z1
        assert state(x, y - 1, z).split("[")[0] not in ("minecraft:air", "minecraft:barrier")    # the hall floor
        for dy in (0, 1):                                                # the free space of the hall: barriers
            s = state(x, y + dy, z)
            assert s == "minecraft:barrier" or aoe2mc.passable_states([s])[0], (x, z, s)
        assert any(state(x, h, z) not in ("minecraft:air", "minecraft:barrier") for h in range(y + 2, y + 12)), \
            (x, z)                                                       # under the roof, not on the roof of a shed
