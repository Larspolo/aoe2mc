"""game/bot.py: a bot defends its villagers against a predator (#3399). The 3 nearest villagers hunt it, then go back
to their last task."""
import math

from test_bot_gather import bot_map

from game import bot


def wolf_map(steps=0):
    server, me, b = bot_map()
    for _ in range(steps):                                             # the villagers go to work first
        b.step()
    b.g.prey["w1"] = "WOLF"
    server.entities["w1"] = {"Pos": (25.5, 64.0, 19.5), "Health": 25.0}  # next to villager b0
    return server, me, b


def test_the_nearest_villagers_attack_the_wolf_and_go_back_to_work():
    server, me, b = wolf_map(20)
    work = {u: (v.res, v.tree) for u, v in b.g.villagers.items()}
    assert all(t for _, t in work.values())
    b.time += bot.LOOK
    b.defend()
    hunters = {u for u, v in b.g.villagers.items() if v.prey == "w1"}
    gap = {u: math.dist((v.pos[0], v.pos[2]), (25.5, 19.5)) for u, v in b.g.villagers.items()}
    assert hunters == set(sorted(gap, key=gap.get)[:3])                # the 3 nearest to the wolf
    assert all(b.g.villagers[u].res == "food" for u in hunters)
    del b.g.prey["w1"]                                                 # killed
    for u in hunters:
        b.g.villagers[u].prey, b.g.villagers[u].tree, b.g.villagers[u].state = None, None, "idle"
    b.time += bot.LOOK
    b.defend()
    assert {u: (b.g.villagers[u].res, b.g.villagers[u].tree) for u in hunters} == {u: work[u] for u in hunters}
    assert not b.defense


def test_a_wolf_out_of_sight_gets_no_defenders():
    server, me, b = wolf_map()
    server.entities["w1"]["Pos"] = (2.5, 64.0, 28.5)
    b.defend()
    assert not b.defense and all(v.prey is None for v in b.g.villagers.values())
