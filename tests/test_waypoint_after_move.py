"""game/gather.py: a sneak right click after a normal move order adds a waypoint after the move, as the Shift click of
AoE2 (#3805, found by the check #3519): the units walk to point 1, then 2, then 3. Fake server."""
from test_move_order import moves, setup
from test_waypoints import arrive, click, sneaking

from game import gather


def test_a_normal_click_then_two_sneak_clicks_walk_the_three_points_in_order():
    server, g = setup(militia=2, villagers=0)
    sneaking(server)
    g.choose({"m0", "m1"}, "m0")
    click(server, g, (10, 4), False)
    click(server, g, (10, 12), True)
    click(server, g, (16, 12), True)
    assert g.waypoints == {"m0": [(10, 12), (16, 12)], "m1": [(10, 12), (16, 12)]}
    assert all(abs(z - 4.5) <= 2 for _, z in moves(server).values())        # only point 1 so far
    for z, x in ((12, 10), (12, 16)):
        server.log.clear()
        arrive(server, g)
        gather.waypoint(g)
        to = moves(server)
        assert set(to) == {"m0", "m1"} and all(abs(p[0] - x - 0.5) <= 2 and abs(p[1] - z - 0.5) <= 2 for p in to.values())
    arrive(server, g)
    gather.waypoint(g)
    assert g.waypoints == {}
