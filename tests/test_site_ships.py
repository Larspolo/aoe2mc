"""game/build.py: a new dock or fish trap foundation moves the ships on its footprint to the water next to it, as AoE2
moves the units off a foundation (#3112). Fake server, no Minecraft."""
from test_fish_trap import built, feudal
from test_ship_gather import fish_map

from game import build, fleet


def put(server, g, uuid, x, z):
    """Put the own ship uuid on the water cell (x, z)."""
    pos = (x + 0.5, g.map.sea(x, z), z + 0.5)
    server.entities.setdefault(uuid, {})["Pos"] = pos
    g.ships[uuid].pos, g.ships[uuid].path = pos, []


def test_a_new_dock_moves_the_ship_on_its_footprint_to_the_water():
    server, g, uuid = fish_map()
    put(server, g, uuid, 15, 15)
    build.found(g, "DOCK", (14, 17, 14, 17))
    x, _, z = g.ships[uuid].pos
    cell = (int(x), int(z))
    assert g.map.wet(*cell) and cell in g.map.around({(a, b) for a in range(14, 17) for b in range(14, 17)}, water=True)
    assert not any(c.startswith(f"tp {uuid} 13.5") for c in server.log)   # not onto the land
    assert fleet.order(g, {uuid}, (20, 20))                              # it can sail again


def test_a_ship_under_a_new_fish_trap_sails_out_and_builds_it():
    server, g, uuid = feudal()
    put(server, g, uuid, 18, 6)                                         # inside the trap TRAP (17, 20, 5, 8)
    site = built(g, uuid)
    x, _, z = g.ships[uuid].pos
    assert not (17 <= x < 20 and 5 <= z < 8)
    assert site["progress"] >= 1


def test_on_paper_a_boat_of_another_player_goes_to_the_water():
    server, g, uuid = fish_map()
    g.paper = True
    boat = "b2"
    where = g.where
    g.where = lambda want, sel: {boat: (15.5, 63.0, 15.5)} if "#minecraft:boat" in sel else (
        {} if want is None else where(want, sel))
    moved = build.clear(g, {(x, z) for x in range(14, 17) for z in range(14, 17)})
    assert g.map.wet(*moved[boat]) and moved[boat][0] >= 14
    assert any(c.startswith(f"tp {boat} ") for c in server.log)
