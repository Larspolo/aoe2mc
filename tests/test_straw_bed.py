"""Straw beds in the camps, the mill and the barracks (#541): poor sleeping places, not beds in the player color."""
import mcvalid
import numpy as np
import pytest

import aoe2mc
import buildings


@pytest.mark.parametrize("arch", ["western", "east_asian"])                 # windmill and granary mills
@pytest.mark.parametrize("name", ["BARRACKS", "MILL", "LUMBER_CAMP", "MINING_CAMP"])
def test_straw_beds(name, arch):
    fn, kw = buildings.select(name)
    w = buildings.footprint(name) * 4
    c = buildings.Canvas(aoe2mc.B, w, height=20)
    c.rng = np.random.default_rng(1)
    fn(c, w, buildings.ARCH[arch], "blue", 4, {"name": name}, **kw)
    beds = {}
    for x in range(w):
        for y in range(20):
            for z in range(w):
                s = aoe2mc.B.states[c.get(x, y, z)] if c.get(x, y, z) >= 0 else ""
                if "_bed[" in s:
                    assert s.removeprefix("minecraft:").startswith("straw_bed["), s
                    assert mcvalid.block_error(s) is None, s
                    beds.setdefault(s.split("part=")[1].rstrip("]"), []).append((x, y, z))
    assert beds.get("head") and len(beds["head"]) == len(beds["foot"])
    air = c.id("air")
    for x, y, z in beds["head"]:                                           # a free way: air next to and above
        assert c.get(x, y + 1, z) in (air, -1)
