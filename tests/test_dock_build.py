"""game/build.py: a player builds a dock on water next to the shore (#1382). Fake server, no Minecraft."""
from test_build_site import Server
from test_gather import grid

from game import build, fleet, gather


def shore_map(wood=200):
    """A flat 24 x 24 map (tile size 1): land at x < 14 (y 64), water at x >= 14 (its surface at y 63)."""
    rows = [[64] * 14 + ["-"] * 10 for _ in range(24)]
    data = grid(rows, [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]}])
    data["players"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}
    data["level_height"] = 1
    server = Server({"Steve": {"Pos": (12.5, 64.0, 12.5), "Rotation": (-90.0, 40.0)}},
                    build.MENU.index("DOCK") + 1)
    g = gather.Gather(server, data).setup()
    g.stock["wood"] = wood
    return server, g


def test_a_dock_must_be_on_water_next_to_the_land():
    server, g = shore_map()
    assert build.shore(g, (14, 17, 10, 13))                            # touches the land at x = 13
    assert not build.shore(g, (12, 15, 10, 13))                        # 2 columns on land
    assert not build.shore(g, (18, 21, 10, 13))                        # the open water: no land next to it
    assert not build.shore(g, (22, 25, 10, 13))                        # out of the map


def test_the_look_at_the_water_places_the_dock_and_villagers_build_it_from_the_shore():
    server, g = shore_map()
    eye, d = (12.5, 65.62, 12.5), gather.direction(-90, 40)           # look east and down at the water
    assert g.map.pick_ground(eye, d) is None and fleet.pick(g, eye, d) == (15, 12)
    site = build.place(g, "Steve", "DOCK", eye, d)
    assert site is g.sites[0] and site["footprint"] == (14, 17, 11, 14) and site["commands"]
    assert g.stock["wood"] == 200 - build.COSTS["DOCK"]["wood"] and server.chosen == 0
    wool = [c.split() for c in server.log if c.startswith("setblock ") and c.endswith("_wool")]
    assert len(wool) == 8 and all(w[2] == "63" for w in wool)          # the ring on the water surface
    goals = g.map.around({(x, z) for x in range(14, 17) for z in range(11, 14)})
    assert goals and all(x == 13 for x, _ in goals)                   # the builders stand on the shore


def test_a_dock_on_land_or_on_the_open_water_is_refused():
    server, g = shore_map()
    assert build.place(g, "Steve", "DOCK", (8.5, 65.62, 12.5), gather.direction(-90, 40)) is None   # land
    assert any("A dock must stand on water next to the shore." in c for c in server.log)
    assert build.place(g, "Steve", "DOCK", (14.5, 70.0, 12.5), gather.direction(-90, 50)) is None   # far out
    assert not g.sites and g.stock["wood"] == 200
