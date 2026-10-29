"""game/bot.py: the bot of player 2 attacks with a group of soldiers (#1051). The armed bot of test_bot_attack."""
from test_bot_attack import armed, orders, steps


def test_no_attack_before_the_group_is_full():
    server, me, b = armed(n=2, attack=0.0)
    b.group = 3
    steps(b, 4)
    assert orders(server) == []                                        # 2 soldiers stay at their building
    server.entities["m2"] = {"Pos": (19.5, 64.0, 26.5), "Rotation": (0.0, 0.0)}
    b.g.soldiers["m2"] = "MILITIA"
    steps(b, 4)
    assert sorted(orders(server)) == [["m0", "p1"], ["m1", "p1"], ["m2", "p1"]]


def test_a_new_soldier_waits_for_its_wave_and_a_dead_wave_waits_again():
    server, me, b = armed(n=2, attack=0.0)
    steps(b, 4)
    assert len(orders(server)) == 2
    del server.entities["m1"]                                          # one dies: the wave goes on
    server.entities["m2"] = {"Pos": (19.5, 64.0, 26.5), "Rotation": (0.0, 0.0)}
    b.g.soldiers["m2"] = "MILITIA"
    start = len(server.log)
    steps(b, 4)
    assert orders(server, start) == []                                 # it waits for a full wave (#3953)
    del server.entities["m0"], server.entities["m2"]                   # the wave is dead
    steps(b, 4)
    assert not b.charged
    server.entities["m3"] = {"Pos": (19.5, 64.0, 27.5), "Rotation": (0.0, 0.0)}
    b.g.soldiers["m3"] = "MILITIA"
    start = len(server.log)
    steps(b, 4)
    assert orders(server, start) == [] and not b.charged
