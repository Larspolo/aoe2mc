"""game/hill.py: the owner of the monument gets hill.TRICKLE of each resource per game second (AoE2 wiki "Monument", #2370), and a
King of the Hill map with no MONUMENT gets one in its center at the first tick. The map of test_king_of_the_hill."""
from test_king_of_the_hill import run, setup

from game import hill


def test_the_owner_gets_the_trickle_of_each_resource():
    server, g = setup(("a", 1, 18.5, 16.5), ("e", 2, 30.5, 30.5))
    hill.tick(g, 0.0)                                                  # the first check: player 1 takes the monument
    start = dict(g.stock)
    run(g, 60)
    assert {r: g.stock[r] - start[r] for r in hill.RESOURCES} == dict.fromkeys(hill.RESOURCES, round(hill.TRICKLE * 60))


def test_a_player_that_does_not_hold_the_monument_gets_nothing():
    server, g = setup(("a", 1, 2.5, 2.5), ("e", 2, 30.5, 30.5))
    start = dict(g.stock)
    run(g, 60)
    assert g.hill["owner"] is None and g.stock == start
    server, g = setup(("a", 1, 2.5, 2.5), ("e", 2, 16.5, 18.5))      # player 2 holds it: player 1 gets nothing
    start = dict(g.stock)
    run(g, 60)
    assert g.hill["owner"] == 2 and g.stock == start


def test_a_map_without_a_monument_gets_one_in_its_center():
    server, g = setup(("a", 1, 2.5, 2.5), monument=False)
    n = len(server.log)
    hill.tick(g, 1.0)
    drawn = server.log[n:]
    assert len([c for c in drawn if c.startswith(("fill ", "setblock "))]) > 10
    assert (16, 16) in g.map.blocked and (2, 2) not in g.map.blocked  # the center: paths go around it
    n = len(server.log)
    hill.tick(g, 1.0)
    assert not any(c.startswith(("fill ", "setblock ")) for c in server.log[n:])   # only once


def test_a_map_with_a_monument_gets_no_second_one():
    server, g = setup(("a", 1, 2.5, 2.5))
    assert hill.place(g) == []


def test_the_monument_goes_next_to_a_building_in_the_center():
    server, g = setup(("a", 1, 2.5, 2.5), monument=False)
    g.map.blocked |= {(x, z) for x in range(14, 19) for z in range(14, 19)}   # a building in the center
    before = set(g.map.blocked)
    hill.tick(g, 1.0)
    new = g.map.blocked - before
    assert new and not new & {(x, z) for x in range(14, 19) for z in range(14, 19)}
    (cx, cz), xs, zs = hill.center(g), [x for x, _ in new], [z for _, z in new]   # the timer counts there
    assert min(xs) <= cx * g.map.T <= max(xs) + 1 and min(zs) <= cz * g.map.T <= max(zs) + 1
