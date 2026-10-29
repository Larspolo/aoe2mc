"""game/bot.py: the soldiers of the bot attack an enemy unit in its town, also before the attack time (#3954)."""
from test_bot_attack import armed, orders

from game import bot, owners


def town(team=None):
    """armed() with the attack at 10:00 and a soldier of player 1 next to the bot town center."""
    server, me, b = armed(attack=600.0, sight=True)
    if team:
        b.g.data["players"] |= {"1": {"team": team}, "2": {"team": team, **b.g.data["players"]["2"]}}
        b.g.enemies.pop("p1")                                          # an ally from the start (owners.add)
    me.bots = [b]                                                      # run.play: build.sides
    me.soldiers["e1"] = "MILITIA"                                      # trained by player 1 (owners.add)
    owners.add(me, "e1", "MILITIA", 1)
    server.entities["e1"] = {"Pos": (19.5, 64.0, 21.5), "Rotation": (0.0, 0.0)}
    return server, me, b


def test_the_bot_soldiers_attack_an_enemy_in_the_town_before_the_attack_time():
    server, me, b = town()
    b.step()
    assert sorted(orders(server)) == [["m0", "e1"], ["m1", "e1"]]


def test_an_allied_soldier_in_the_town_gets_no_attack_order():
    server, me, b = town(team=1)
    b.step()
    assert orders(server) == []


def test_after_the_enemy_dies_the_soldiers_go_back():
    server, me, b = town()
    b.step()
    del server.entities["e1"]
    n = len(server.log)
    b.time = b.guarded + bot.LOOK                                      # the next look
    b.orders()
    back = [c.split()[2:] for c in server.log[n:] if c.startswith("aoe moveto ")]
    assert sorted(back) == [["m0", "19.5", "64.0", "24.5"], ["m1", "19.5", "64.0", "25.5"]]
    assert b.guards == {}
