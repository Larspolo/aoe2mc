"""Gather.fall with two sides that share a target (#3005): a building that two sides attack falls once, the other side
forgets it, and a target with no box in forts falls with no error. Fake server of test_gather."""
from test_gather import FakeServer, grid
from test_wonder import targets

from game import combat, gather, run

HOUSE = [15, 15, 17, 17]                                               # a house of player 3


def two_sides(objects=()):
    server = FakeServer({})
    rows = grid([[64] * 24 for _ in range(24)], objects)
    g, g2 = gather.Gather(server, rows).setup(), gather.Gather(server, rows).setup()
    g.bots = [run.Side(g2)]
    g2.peers = [g]
    return server, g, g2


def house(objects=()):
    return [{"kind": "building", "name": "HOUSE", "player": 3, "tile": [16, 16], "footprint": HOUSE}, *objects]


def test_a_house_that_two_sides_attack_falls_with_no_error_and_leaves_every_set():
    server, g, g2 = two_sides(house())
    uuid = combat.target_uuid(HOUSE)
    g.sieged.add(uuid)
    g2.sieged.add(uuid)                                                # both sides attack the same house
    targets(server, set())                                             # the plugin removed the house
    g.fall()
    g2.fall()                                                          # no KeyError: g dropped the house for g2
    assert uuid not in g.sieged | g2.sieged
    assert uuid not in g.forts and uuid not in g2.forts


def test_the_loot_and_the_razing_count_once_for_a_shared_target():
    server, g, g2 = two_sides(house())
    uuid = combat.target_uuid(HOUSE)
    g.sieged.add(uuid)
    g2.sieged.add(uuid)
    targets(server, set())
    g.fall()
    g2.fall()
    assert vars(g).get("razed", {}).keys() == {uuid}
    assert "razed" not in vars(g2)


def test_a_target_with_no_box_in_forts_falls_with_no_error():
    server, g, g2 = two_sides()
    g.sieged.add("00000000-0000-0000-0000-00000000dead")               # a target that has no entry in forts
    g2.sieged.add("00000000-0000-0000-0000-00000000dead")
    targets(server, set())
    g.fall()
    g2.fall()
    assert not g.sieged and not g2.sieged
