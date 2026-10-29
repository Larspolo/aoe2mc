"""game/bot.py: one game of the bot in the order of its strategy (#3949): the economy technology, then the Blacksmith
technology, then the upgrade of its unit line, then a wave of soldiers. Fake server of test_gather, the map of
test_bot_gather."""
import re

import pytest
from test_bot_attack import orders, steps
from test_bot_gather import bot_map

from game import bot

train = bot.train                                                     # the module that bot uses


def strategy():
    """A bot of the Feudal Age with its villager number, a lumber camp, a barracks, a blacksmith and two militia."""
    server, me, b = bot_map()
    b.villagers = len(b.g.villagers)
    b.g.techs.update(bot.build.AGE_TECHS[:2])
    b.g.sites.append({"name": "LUMBER_CAMP", "player": 2, "footprint": [26, 28, 20, 22], "done": True})
    b.g.sites.append({"name": "BLACKSMITH", "player": 2, "footprint": [20, 23, 24, 27], "done": True})
    b.g.data["objects"].append({"kind": "building", "name": "BARRACKS", "player": 2, "footprint": [14, 24, 17, 27]})
    b.attack, b.group = 0.0, 2
    b.g.seen_tiles = lambda *a, **k: {(x, z) for x in range(32) for z in range(32)}
    for i in range(2):
        u = f"m{i}"
        server.entities[u] = {"Pos": (19.5, 64.0, 24.5 + i), "Rotation": (0.0, 0.0)}
        b.g.soldiers[u] = "MILITIA"
    server.forts = set()
    command = server.command

    def alive(cmd):                                                    # as test_bot_attack.armed
        if m := re.fullmatch(r"execute if entity (\S+)", cmd):
            return "Test passed" if m[1] in server.entities or m[1] in server.forts else "Test failed"
        return command(cmd)
    server.command = alive
    return server, me, b


def pay(b, name):
    """The stock of exactly one step: its cost and the reserve of the next age (keep), nothing else."""
    b.g.stock.update({r: 0 for r in b.g.stock})
    b.g.stock.update({r: v + b.keep().get(r, 0) for r, v in train.price(b.g, name).items()})


def queued(b):
    return [e["name"] for q in b.g.queues.values() for e in q]


@pytest.mark.xfail(strict=True, reason="#4206: a Blacksmith technology takes the resources of the economy technology")
def test_the_bot_researches_its_strategy_in_order():
    server, me, b = strategy()
    for name in ["DOUBLE_BIT_AXE", "FORGING", "MAN_AT_ARMS_UPGRADE"]:
        pay(b, name)
        b.research()
        assert name in queued(b), name
        b.g.techs.add(name)                                            # the test does not wait for the queue


def test_the_wave_of_the_strategy_attacks_with_one_order_per_soldier():
    server, me, b = strategy()
    steps(b, 4)
    assert sorted(orders(server)) == [["m0", "p1"], ["m1", "p1"]]      # one order for each soldier of the wave
