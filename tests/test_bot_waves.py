"""game/bot.py: after its first wave the bot keeps the new soldiers at home until they are a full wave, then sends all
of them (#3953), as the AoE2 computer player does. The armed bot of test_bot_attack."""
from test_bot_attack import armed, orders, steps


def soldier(server, b, u, z):
    server.entities[u] = {"Pos": (19.5, 64.0, z), "Rotation": (0.0, 0.0)}
    b.g.soldiers[u] = "MILITIA"


def test_the_new_soldiers_attack_as_a_wave():
    server, me, b = armed(n=2, attack=0.0)
    steps(b, 4)
    assert sorted(u for u, _ in orders(server)) == ["m0", "m1"]       # the first wave, at the same time as before
    soldier(server, b, "m2", 26.5)
    start = len(server.log)
    steps(b, 4)
    assert orders(server, start) == [] and b.wave == {"m0", "m1"}      # 1 new soldier waits
    soldier(server, b, "m3", 27.5)
    start = len(server.log)
    steps(b, 4)
    assert sorted(orders(server, start)) == [["m2", "p1"], ["m3", "p1"]]   # 2 waiting soldiers: the next wave
    assert b.wave == {"m0", "m1", "m2", "m3"}
