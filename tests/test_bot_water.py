"""game/bot.py: a land soldier of the bot does not attack a ship on the water (#1658): it cannot walk there."""
from test_bot_attack import armed, orders


def lake(b, x0, x1):
    """Water (no ground) in the block columns x0 to x1 - 1 of the map."""
    for row in b.g.map.ground:
        row[x0:x1] = [None] * (x1 - x0)


def test_a_melee_soldier_attacks_the_far_unit_on_the_land_and_not_the_near_ship():
    server, me, b = armed(attack=0.0)
    lake(b, 8, 16)
    me.soldiers["ship"] = "TRANSPORT_SHIP"
    server.entities["ship"] = {"Pos": (14.5, 63.0, 24.5)}             # 5 blocks from the militia, on the water
    server.entities["p1"]["Pos"] = (2.5, 64.0, 2.5)
    b.fight()
    assert sorted(orders(server)) == [["m0", "p1"], ["m1", "p1"]]


def test_only_a_ranged_soldier_in_range_shoots_at_a_ship():
    server, me, b = armed(attack=0.0)
    lake(b, 8, 18)
    del server.entities["p1"]
    me.soldiers["ship"] = "TRANSPORT_SHIP"
    server.entities["ship"] = {"Pos": (16.5, 63.0, 24.5)}             # 3 blocks (tiles, T = 1) from m0
    b.g.soldiers["m1"] = "ARCHER"                                      # range 4
    b.fight()
    assert orders(server) == [["m1", "ship"]]                         # the militia gets no target on the water
    server.entities["ship"]["Pos"] = (9.5, 63.0, 24.5)                # out of range: no order
    b.targets.clear()
    n = len(server.log)
    b.fight()
    assert orders(server, n) == []
