"""game/build.py: a building of 3 × 3 tiles or more needs one elevation level under it, a Town Center also for the
Thracians, whose other buildings stand on any elevation (AoE2 wiki "Elevation" and "Thracians", #2545, epic #1088)."""
from test_gather import FakeServer, grid

from game import build, gather

HILL = 24                                                              # blocks x >= HILL are one level up


def hill_map(civ):
    """A 48 × 48 block map (tile size 4, level height 3): the east half is one level higher."""
    data = grid([[64 + 3 * (x >= HILL) for x in range(48)] for _ in range(48)])
    data.update(tile_size=4, level_height=3, players={"1": {"civ": civ, "color": "blue", "arch": "western"}})
    server = FakeServer({"Steve": {"Pos": (9.5, 64.0, 9.5)}})
    g = gather.Gather(server, data, start={}).setup()
    g.stock.update(food=1000, wood=1000, stone=1000, gold=1000)
    return server, g


def placed(g, name, cell):
    g.map.pick_ground = lambda eye, d: cell
    return build.place(g, "Steve", name, (0, 70, 0), (0, -1, 0))


def test_a_large_building_on_the_edge_of_a_hill_is_refused():
    server, g = hill_map("BRITONS")
    assert placed(g, "BARRACKS", (HILL, 10)) is None
    assert any("flat ground" in c for c in server.log if c.startswith("tellraw"))
    assert placed(g, "BARRACKS", (10, 10))                             # on one level


def test_a_small_building_and_a_farm_stand_on_any_elevation():
    _, g = hill_map("BRITONS")
    assert placed(g, "HOUSE", (HILL, 10))
    assert placed(g, "FARM", (HILL, 30))


def test_the_thracians_build_on_any_elevation_but_the_town_center():
    _, g = hill_map("THRACIANS")
    assert placed(g, "BARRACKS", (HILL, 10))
    assert placed(g, "TOWN_CENTER", (HILL, 30)) is None
    assert build.level(g, "TOWN_CENTER", (4, 20, 4, 20))
