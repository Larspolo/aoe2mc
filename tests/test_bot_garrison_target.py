"""game/bot.py: a soldier of the bot does not attack a unit inside a building (#3429)."""
from test_bot_attack import armed, orders

from game import combat


def test_a_target_that_goes_inside_is_dropped_for_a_unit_outside():
    server, me, b = armed(attack=0.0)
    me.villagers["far"] = me.villagers["p1"]
    server.entities["far"] = {"Pos": (1.5, 64.0, 1.5)}
    b.fight()
    assert sorted(orders(server)) == [["m0", "p1"], ["m1", "p1"]]
    me.garrisons[(2, 2, 5, 5)] = ["p1"]                                # p1 goes into a building: it lives there
    n = len(server.log)
    b.fight()
    assert sorted(orders(server, n)) == [["m0", "far"], ["m1", "far"]]


def test_a_target_that_goes_inside_is_dropped_for_a_building_when_no_unit_is_outside():
    server, me, b = armed(attack=0.0)
    tc = combat.target_uuid([2, 2, 5, 5])                              # the town center of player 1
    server.forts.add(tc)
    b.fight()
    assert sorted(orders(server)) == [["m0", "p1"], ["m1", "p1"]]
    me.garrisons[(2, 2, 5, 5)] = ["p1"]
    n = len(server.log)
    b.fight()
    assert sorted(orders(server, n)) == [["m0", tc], ["m1", tc]] and tc in b.g.sieged
