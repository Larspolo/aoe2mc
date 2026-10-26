"""game/build.py: the wool ring of a construction site stays until the building is complete (owner request)."""
from test_build_rise import build_with, rise_map

from game import build


def world(cmds):
    """The blocks that a list of /setblock and /fill commands makes (a fake world)."""
    out = {}
    for c in cmds:
        if (b := build.box(c)):
            (x0, y0, z0, x1, y1, z1), state = b
            out.update({(x, y, z): state for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)
                        for z in range(z0, z1 + 1)})
    return out


def test_the_ring_stays_while_the_building_rises():
    server, g = rise_map()
    site, = g.sites
    ring = site["ring"]
    assert len(ring) == 28 and all(world(server.log)[c] == "minecraft:blue_wool" for c in ring)
    g.select("v0")
    g.click("Steve")
    seen = 0
    for _ in range(1000):
        g.step()
        if 0 < site["progress"] < 1 and site["sent"]:
            w = world(server.log)
            assert all(w[c] == "minecraft:blue_wool" for c in ring), site["progress"]
            seen += 1
        if site["progress"] >= 1:
            break
    assert seen > 3


def test_a_complete_building_has_its_own_blocks_on_the_ring():
    server, g = rise_map()
    site, = g.sites
    before = world(server.log)
    site, _, _ = build_with(server, g, ["v0"])
    assert site["progress"] == 1
    w, design = world(server.log), world(site["commands"])
    for c in site["ring"]:
        assert w[c] == design.get(c, "minecraft:air"), c
    assert "minecraft:blue_wool" not in {w[c] for c in site["ring"]}
    assert before.keys() <= w.keys()
