"""game/bot.py: the soldiers of a bot help an ally whose town an enemy attacks (#4021). The fake game of
test_bot_defend."""
from test_bot_attack import orders
from test_bot_defend import town

from game import owners


def allied(near_own=False):
    """town() with player 3 an ally of the bot (player 2) with a house far from the bot town, and the soldier e1 of
    player 1 next to that house (and also next to the bot town center with near_own)."""
    server, me, b = town()
    b.g.data["players"] |= {"2": {"team": 2, **b.g.data["players"]["2"]}, "3": {"team": 2}}
    b.g.data["objects"].append({"kind": "building", "name": "HOUSE", "player": 3, "footprint": [2, 28, 3, 29]})
    server.entities["e1"]["Pos"] = (3.5, 64.0, 27.5)
    if near_own:
        me.soldiers["e2"] = "MILITIA"
        server.entities["e2"] = {"Pos": (19.5, 64.0, 21.5), "Rotation": (0.0, 0.0)}
        owners.add(me, "e2", "MILITIA", 1)
    return server, me, b


def test_the_soldiers_attack_an_enemy_in_the_town_of_an_ally():
    server, me, b = allied()
    b.step()
    assert sorted(orders(server)) == [["m0", "e1"], ["m1", "e1"]]


def test_no_order_without_the_ally():
    server, me, b = allied()
    del b.g.data["players"]["3"]
    b.step()
    assert orders(server) == []


def test_the_own_town_comes_first():
    server, me, b = allied(near_own=True)
    b.step()
    assert sorted(orders(server)) == [["m0", "e2"], ["m1", "e2"]]
