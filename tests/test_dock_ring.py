"""game/build.py: a complete dock keeps no border in the player color (#2059). The owner saw the painted deck edge of
the dock design (blue concrete) as the foundation ring. Fake server, no Minecraft."""
import re

from test_dock_build import shore_map

from game import build, gather


def water_server(server):
    """The fake server answers "execute if block X Y Z minecraft:water" for the water cells (x >= 14) at y 63."""
    command = server.command

    def answer(cmd):
        if m := re.fullmatch(r"execute if block (\S+) (\S+) (\S+) minecraft:water", cmd):
            server.log.append(cmd)
            return "Test passed" if int(m[1]) >= 14 and m[2] == "63" else "Test failed"
        return command(cmd)
    server.command = answer
    return server


def test_a_complete_dock_has_no_wool_and_no_hole_in_the_water():
    server, g = shore_map()
    water_server(server)
    site = build.place(g, "Steve", "DOCK", (12.5, 65.62, 12.5), gather.direction(-90, 40))
    assert all(state.endswith("_wool") for state in site["ring"].values())
    assert not build.rise(g, site, 10) and build.rise(g, site, 1e9)
    last = {}
    for c in server.log:                                               # the last block at each ring cell
        if b := build.box(c):
            (x0, y0, z0, x1, y1, z1), state = b
            for p in site["ring"]:
                if x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and z0 <= p[2] <= z1:
                    last[p] = state
    assert set(last) == set(site["ring"])
    assert not [p for p, s in last.items() if "wool" in s or s == "minecraft:air"], last   # water or the design


def test_the_dock_design_has_no_deck_edge_in_the_player_color():
    server, g = shore_map()
    site = build.place(g, "Steve", "DOCK", (12.5, 65.62, 12.5), gather.direction(-90, 40))
    assert site["commands"] and not [c for c in site["commands"] if "blue_concrete" in c or "blue_wool" in c]
    assert any("blue_banner" in c for c in site["commands"])           # the player color stays on banners and flag
