"""The bell of a monastery hangs in the belfry of its tower, not over the nave (#3094)."""
import numpy as np
import pytest

import aoe2mc
import buildings

SETS = ("western", "central", "mediterranean", "east_asian", "southeast_asian", "mesoamerican")


def blocks(monkeypatch, name, arch, tile):
    monkeypatch.setattr(buildings, "BARRIERS", False)
    size = 16
    cols = aoe2mc.Columns(size, np.zeros((size, size), np.int16), np.zeros((size, size), np.float32),
                          {0: "GRASS_1"}, tile, 3, np.random.default_rng(1))
    E = aoe2mc.Edits(cols)
    o = dict(kind="B", name=name, player=1, x=8.0, y=8.0, rotation=0.0, hero=False, garrisoned=False)
    buildings.place_building(E, cols, aoe2mc.B, o, {1: {"color": "blue", "arch": arch}}, set(), {})
    last = {}
    for x, y, z, ids, _ in E.parts:
        for p in zip(x.tolist(), y.tolist(), z.tolist(), ids.tolist()):
            last[p[:3]] = aoe2mc.B.states[p[3]].split(":")[1]
    return last


@pytest.mark.parametrize("tile", (3, 4, 5, 6))
@pytest.mark.parametrize("arch", SETS)
@pytest.mark.parametrize("name", ("MONASTERY", "ROCK_CHURCH"))
def test_bell_hangs_in_the_belfry(monkeypatch, name, arch, tile):
    last = blocks(monkeypatch, name, arch, tile)
    bells = [p for p, s in last.items() if s.startswith("bell")]
    assert len(bells) == 1
    x, y, z = bells[0]
    above = last.get((x, y + 1, z), "air")
    assert above != "air" and not above.startswith("bell")
    # the corner pillars of the belfry are next to the bell, at its height
    pillars = [(dx, dz) for dx in range(-2, 3) for dz in range(-2, 3) if (dx or dz) and last.get((x + dx, y, z + dz), "air") != "air"]
    assert len(pillars) == 4
