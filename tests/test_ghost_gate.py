"""game/build.py: the ghost of a gate lies on the wall line under the cursor, along x or along z (#1357). Fake server."""
from test_ghost import ghost

from game import build, gather


def parts(server):
    """The (x, z) of the parts of the last ghost shape, relative to the tile under the cursor."""
    shape = [c for c in server.log if c.startswith("aoe ghost-shape Steve 1 ")]
    return {(int(t.split("/")[0]), int(t.split("/")[2])) for c in shape for t in c.split()[4:]}


def setup():
    server, g = ghost(build.MENU.index("PALISADE_GATE") + 1)
    g.stock["wood"] = 1000
    cell = g.map.pick_ground((8.5, 65.62, 12.5), gather.direction(-90, 30))   # the look of Steve
    return server, g, cell


def line(g, a, b):
    chosen = g.game.chosen
    build.wall(g, "Steve", "PALISADE_WALL", a)
    build.wall(g, "Steve", "PALISADE_WALL", b)
    g.game.chosen = chosen                                            # the gate stays chosen


def test_the_ghost_of_a_gate_follows_a_wall_along_z():
    server, g, (x, z) = setup()
    line(g, (x, z - 1), (x, z + 2))                                   # the cursor is on the second tile
    server.log.clear()
    build.tick(g)
    assert {p[0] for p in parts(server)} == {0} and {p[1] for p in parts(server)} == {-1, 0, 1, 2}
    assert "aoe ghost-color Steve green" in server.log and "aoe ghost Steve 1 1" in server.log
    assert g.ghosts["Steve"][2] == build.gate_rect(g, (x, z)) == (x, x + 1, z - 1, z + 3)


def test_the_ghost_of_a_gate_follows_a_wall_along_x_and_is_red_off_a_wall():
    server, g, (x, z) = setup()
    server.log.clear()
    build.tick(g)                                                     # no wall: along x, red
    assert {p[0] for p in parts(server)} == {-2, -1, 0, 1} and {p[1] for p in parts(server)} == {0}
    assert "aoe ghost-color Steve red" in server.log
    line(g, (x - 3, z), (x, z))                                       # (the tree of tile (12, 12) is east)
    server.log.clear()
    build.tick(g)                                                     # a wall: the ghost moves on its 4 tiles
    assert {p[0] for p in parts(server)} == {-3, -2, -1, 0} and "aoe ghost-color Steve green" in server.log
    server.log.clear()
    build.tick(g)
    assert not any(c.startswith("aoe ghost") for c in server.log)      # the same look: nothing new
