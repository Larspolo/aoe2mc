"""The Colosseum and the Amphitheatre have stepped seats, an arena with props and a gate passage (#451)."""
from collections import Counter

import mcvalid
import pytest
from test_furnish_landmarks import blocks

import aoe2mc

NEEDS = {"COLOSSEUM": ("iron_bars", "hay_block", "lantern", "blue_wall_banner", "smooth_quartz_stairs", "red_carpet"),
         "AMPHITHEATRE": ("iron_bars", "lantern", "blue_wall_banner", "dark_oak_slab", "potted_fern")}


@pytest.mark.parametrize("arch", ["western", "middle_eastern"])
@pytest.mark.parametrize("name", sorted(NEEDS))
def test_arena_is_furnished(name, arch):
    last = blocks(name, arch)
    names = Counter(s.split("[")[0] for s in last.values())
    assert all(names[n] >= 1 for n in NEEDS[name]), (name, arch, {n: names[n] for n in NEEDS[name]})
    assert mcvalid.invalid_states(aoe2mc.B.states) == {}


@pytest.mark.parametrize("name", sorted(NEEDS))
def test_gate_passage_reaches_the_arena(name):
    last = blocks(name, "western")
    xs = sorted({p[0] for p in last}); zs = sorted({p[2] for p in last})
    y0 = min(p[1] for p in last)
    m = (xs[0] + xs[-1] + 1) // 2
    free = ("air", "barrier", "sand")
    for z in range((zs[0] + zs[-1] + 1) // 2, zs[-1] + 1):               # from the centre out to the south side
        assert last.get((m, y0 + 1, z), "air").split("[")[0] in free, (name, z, last[(m, y0 + 1, z)])


@pytest.mark.parametrize("tile", [1, 2, 3])
@pytest.mark.parametrize("name", sorted(NEEDS))
def test_small_tile_sizes_work(name, tile):
    blocks(name, "western", tile)


@pytest.mark.parametrize("name", sorted(NEEDS))
def test_seats_step_down_to_the_arena(name):
    last = blocks(name, "western")
    xs = sorted({p[0] for p in last}); zs = sorted({p[2] for p in last})
    z = (zs[0] + zs[-1] + 1) // 2

    def top(x):
        ys = [y for (bx, y, bz), s in last.items() if bx == x and bz == z and s.split("[")[0] not in ("air", "barrier")]
        return max(ys)
    tops = [top(x) for x in range(xs[0] + 2, xs[0] + 6)]
    assert tops == sorted(tops, reverse=True) and tops[0] > tops[-1], tops
