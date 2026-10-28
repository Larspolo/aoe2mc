"""The round middle_eastern towers have a closed wall: no slit from the ground to the lookout (#3096)."""
import numpy as np
import pytest

import aoe2mc
import buildings

KINDS = ("watch", "guard", "bombard", "keep")


def draw(w, kind, arch="middle_eastern"):
    c = buildings.Canvas(aoe2mc.B, w, height=40)
    c.rng = np.random.default_rng(1)
    buildings.tower(c, w, buildings.ARCH[arch], "blue", 4, {}, kind=kind)
    name = lambda x, y, z: aoe2mc.B.states[c.get(x, y, z)].removeprefix("minecraft:").split("[")[0] \
        if c.get(x, y, z) >= 0 else None
    return c, name


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("w", (4, 5, 6, 8, 12))
def test_no_air_cell_of_the_shaft_touches_the_outside(w, kind):
    c, get = draw(w, kind)
    hb = max({"watch": 12, "guard": 14, "bombard": 14, "keep": 16}[kind], 8)
    slits = [(x, y, z) for x in range(w) for y in range(1, hb - 1) for z in range(w) if get(x, y, z) == "air"
             and any(get(x + dx, y, z + dz) is None for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    assert slits == []
    cells = [(x, y, z) for x in range(w) for y in range(1, hb + 2) for z in range(w)]
    ladder = [(x, y, z) for x, y, z in cells if get(x, y, z) == "ladder"]
    assert ladder and all(get(x, y, z - 1) not in (None, "air", "ladder") for x, y, z in ladder)   # a wall behind
    assert any(get(*p) == "barrel" for p in cells) and any(get(*p) == "lantern" for p in cells)
    x, z = next((x, z) for x in range(w) for z in range(w) if "door" in str(get(x, 1, z)))
    assert get(x, 1, z - 1) == get(x, 2, z - 1) == "air"                 # the door opens into the shaft
