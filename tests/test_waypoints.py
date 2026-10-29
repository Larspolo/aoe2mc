"""game/gather.py: a sneak right click on the ground adds a waypoint to the move of the selected units, as the Shift
click of AoE2 (#3515); the units walk to the points in order. A normal click ends the queue. Fake server."""
from test_move_order import moves, setup

from game import gather


def click(server, g, cell, sneak):
    """A right click of Steve on the ground cell (x, z) of the 24 × 24 map, with or without sneak."""
    server.sneak = sneak
    g.map.pick_ground = lambda eye, d: cell
    g.click("Steve")


def sneaking(server):
    """The fake server answers the is_sneaking predicate with server.sneak."""
    command = server.command
    server.sneak = False

    def answer(cmd):
        if cmd == f"execute as Steve if predicate {gather.SNEAK}":
            return "Test passed" if server.sneak else "Test failed"
        return command(cmd)
    server.command = answer


def arrive(server, g):
    """The units stand on their present targets."""
    for u, (x, z) in g.waypoint_at.items():
        server.entities[u]["Pos"] = (x + 0.5, 64.0, z + 0.5)


def queue():
    server, g = setup(militia=2, villagers=0)
    sneaking(server)
    g.choose({"m0", "m1"}, "m0")
    click(server, g, (10, 4), True)
    click(server, g, (10, 12), True)
    click(server, g, (16, 12), True)
    return server, g


def test_sneak_clicks_queue_points_and_the_units_walk_them_in_order():
    server, g = queue()
    assert g.waypoints == {"m0": [(10, 12), (16, 12)], "m1": [(10, 12), (16, 12)]}
    assert all(abs(z - 4.5) <= 2 for _, z in moves(server).values())        # only point 1 so far
    for z, x in ((12, 10), (12, 16)):
        server.log.clear()
        gather.waypoint(g)
        assert not moves(server)                                           # not there yet
        arrive(server, g)
        gather.waypoint(g)
        to = moves(server)
        assert set(to) == {"m0", "m1"} and all(abs(p[0] - x - 0.5) <= 2 and abs(p[1] - z - 0.5) <= 2 for p in to.values())
    assert g.waypoints == {"m0": [], "m1": []}
    arrive(server, g)
    gather.waypoint(g)
    assert g.waypoints == {}


def test_a_normal_click_ends_the_queue():
    server, g = queue()
    click(server, g, (4, 8), False)
    assert g.waypoints == {}
    arrive(server, g)
    server.log.clear()
    gather.waypoint(g)
    assert not moves(server)
