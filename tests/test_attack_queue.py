"""game/gather.py: a sneak right click on an enemy queues an attack target, as the Shift click of AoE2 (#3516). The
units attack the targets in order and walk to the queued points after them. Fake server."""
from test_move_order import moves
from test_move_order import setup as base
from test_waypoints import arrive, click, sneaking

from game import gather


def setup():
    server, g = base(militia=2, villagers=0)
    for e, x in (("eA", 10.5), ("eB", 14.5)):
        server.entities[e] = {"Pos": (x, 64.0, 4.5)}
        g.enemies[e] = "MILITIA"
    sneaking(server)
    g.choose({"m0", "m1"}, "m0")
    return server, g


def hit(server, g, enemy, sneak):
    """A right click of Steve on the enemy unit."""
    server.sneak = sneak
    g.target = lambda *a, **k: ("enemy", enemy, None)
    g.click("Steve")


def ground(server, g, cell, sneak):
    g.target = lambda *a, **k: None
    click(server, g, cell, sneak)


def attacks(server):
    return [c for c in server.log if c.startswith("aoe attack ")]


def test_a_sneak_click_queues_a_second_target():
    server, g = setup()
    server.log.clear()
    hit(server, g, "eA", False)
    hit(server, g, "eB", True)
    assert attacks(server) == [f"aoe attack @e[tag={gather.SELECT}] eA"]       # B waits for A
    assert g.waypoints == {"m0": [{"attack": "eB"}], "m1": [{"attack": "eB"}]}
    gather.waypoint(g)
    assert len(attacks(server)) == 1                                         # A lives
    del server.entities["eA"]
    server.log.clear()
    gather.waypoint(g)
    assert sorted(attacks(server)) == ["aoe attack m0 eB", "aoe attack m1 eB"]
    del server.entities["eB"]
    gather.waypoint(g)
    assert g.waypoints == {}


def test_a_sneak_click_on_an_enemy_then_on_the_ground():
    server, g = setup()
    server.log.clear()
    hit(server, g, "eA", True)
    ground(server, g, (16, 12), True)
    assert attacks(server) == [f"aoe attack @e[tag={gather.SELECT}] eA"]
    assert g.waypoints == {"m0": [(16, 12)], "m1": [(16, 12)]} and not moves(server)
    del server.entities["eA"]
    gather.waypoint(g)
    to = moves(server)
    assert set(to) == {"m0", "m1"} and all(abs(x - 16.5) <= 2 and abs(z - 12.5) <= 2 for x, z in to.values())
    arrive(server, g)
    gather.waypoint(g)
    assert g.waypoints == {}


def test_a_dead_queued_target_is_skipped_and_a_normal_click_ends_the_queue():
    server, g = setup()
    hit(server, g, "eA", True)
    hit(server, g, "eB", True)
    ground(server, g, (16, 12), True)
    del server.entities["eA"], server.entities["eB"]
    server.log.clear()
    gather.waypoint(g)
    assert not attacks(server) and set(moves(server)) == {"m0", "m1"}         # B is dead: the point is next
    hit(server, g, "eA", False)
    assert g.waypoints == {"m0": [], "m1": []}                                 # only the new attack
