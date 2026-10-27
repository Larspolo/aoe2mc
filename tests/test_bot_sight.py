"""game/bot.py: the bot chooses only the units of player 1 in the sight of its own units and buildings, as the AoE2
AI does not see through the fog of war (#2050). Else its soldiers go to the nearest building of player 1."""
from test_bot_attack import armed, orders

from game import combat


def test_a_unit_out_of_sight_is_no_target():
    server, me, b = armed(attack=0.0, sight=True)                      # p1 at tile (6, 6), the bot at (20, 24)
    assert (6, 6) not in b.g.seen_tiles()
    b.fight()
    assert orders(server) == []                                        # no building of player 1 in server.forts
    tc = combat.target_uuid([2, 2, 5, 5])
    server.forts.add(tc)
    b.fight()
    assert sorted(orders(server)) == [["m0", tc], ["m1", tc]]          # the building, not the unit


def test_a_unit_in_sight_is_a_target():
    server, me, b = armed(attack=0.0, sight=True)
    server.entities["p1"]["Pos"] = (17.5, 64.0, 24.5)                  # 2 tiles from the militia
    assert (17, 24) in b.g.seen_tiles()
    b.fight()
    assert sorted(orders(server)) == [["m0", "p1"], ["m1", "p1"]]


def test_a_unit_that_comes_in_sight_goes_before_the_building():
    server, me, b = armed(attack=0.0, sight=True)
    tc = combat.target_uuid([2, 2, 5, 5])
    server.forts.add(tc)
    b.fight()
    n = len(server.log)
    b.fight()
    assert orders(server, n) == []                                     # the same building: no new order
    server.entities["p1"]["Pos"] = (17.5, 64.0, 24.5)
    b.fight()
    assert sorted(orders(server, n)) == [["m0", "p1"], ["m1", "p1"]]
