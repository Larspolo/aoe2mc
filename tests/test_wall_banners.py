"""Each wall banner hangs on the face of the wall, also on a thin wall tile between pillars (#3099)."""
import pytest


def banners(name, T, axis):
    """(banner count, banners with no solid block behind) of a straight wall line of 18 tiles."""
    import aoe2mc
    import buildings
    st, n, floating = buildings.ARCH["western"], 0, 0
    for i in range(18):
        ends = (i > 0, i < 17)
        nb = (*ends, False, False) if axis == "z" else (False, False, *ends)
        o = (0, i * T) if axis == "z" else (i * T, 0)
        c = buildings.Canvas(aoe2mc.B, T, 3 * T + 8)
        buildings.wall_segment(c, T, st, "blue", T, {"name": name, "neighbours": nb, "origin": o})
        for x in range(-1, T + 1):
            for y in range(3 * T + 8):
                for z in range(-1, T + 1):
                    b = c.get(x, y, z)
                    s = aoe2mc.B.states[b] if b >= 0 else "air"
                    if "_wall_banner" not in s:
                        continue
                    n += 1
                    f = s.split("facing=")[1][:-1]
                    dx, dz = {"south": (0, -1), "north": (0, 1), "east": (-1, 0), "west": (1, 0)}[f]
                    k = c.get(x + dx, y, z + dz)
                    behind = aoe2mc.B.states[k] if k >= 0 else "air"
                    floating += behind.split("[")[0] in ("air", "barrier")
    return n, floating


@pytest.mark.parametrize("name", ["STONE_WALL", "FORTIFIED_WALL", "PALISADE_WALL"])
@pytest.mark.parametrize("T", [3, 4, 5, 6])
@pytest.mark.parametrize("axis", ["x", "z"])
def test_each_wall_banner_hangs_on_the_wall(name, T, axis):
    n, floating = banners(name, T, axis)
    assert n == 11                    # 5 banner tiles of 18: two long sides each, and the open end of tile 0
    assert floating == 0
