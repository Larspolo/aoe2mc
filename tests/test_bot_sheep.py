"""game/bot.py: the soldiers of the bot attack the units of player 1, but not its herdable animals (#2049). AoE2: a
soldier does not attack a sheep by itself; an enemy unit near it captures it (herd.tick, tests/test_herd_capture.py)."""
from test_bot_attack import armed, orders


def test_a_sheep_of_player_1_is_no_target():
    server, me, b = armed(attack=0.0)
    b.g.data["objects"].append({"kind": "unit", "name": "SHEEP", "player": 1, "uuid": "s1", "tile": [18.5, 24.5]})
    server.entities["s1"] = {"Pos": (18.5, 64.0, 24.5)}                # next to the militia, the villager far away
    b.fight()
    assert sorted(orders(server)) == [["m0", "p1"], ["m1", "p1"]]
