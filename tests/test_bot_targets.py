"""game/bot.py: when no unit of player 1 is in reach (only a ship on the water lives), the soldiers of the bot attack a
building (#1770: the bot army stayed idle next to the town of player 1)."""
from test_bot_attack import armed, orders
from test_bot_water import lake

from game import combat


def test_with_only_a_ship_on_the_water_the_soldiers_attack_a_building():
    server, me, b = armed(attack=0.0)
    lake(b, 8, 16)
    del server.entities["p1"]
    me.soldiers["ship"] = "TRANSPORT_SHIP"
    server.entities["ship"] = {"Pos": (14.5, 63.0, 24.5)}             # live, but a militia cannot walk to it
    tc = combat.target_uuid([2, 2, 5, 5])                              # the town center of player 1
    server.forts.add(tc)
    b.fight()
    assert sorted(orders(server)) == [["m0", tc], ["m1", tc]] and tc in b.g.sieged
