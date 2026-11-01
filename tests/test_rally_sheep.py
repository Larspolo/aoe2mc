"""A rally point of a town center on an own sheep sends each new villager to hunt it (#5545)."""
from test_train import setup

from game import train

TC = (2, 5, 2, 5)
SHEEP = "sheep-1"


def villager(server, g):
    g.prey[SHEEP], g.flock = 100, {SHEEP}
    server.entities[SHEEP] = {"Pos": (12.5, 64.0, 14.5)}
    train.rally(g, TC, (12, 14), SHEEP)
    train.queue(g, "Steve", (3, 3))
    return train.tick(g, train.TRAIN_TIMES["VILLAGER_MALE"])[0]


def test_a_new_villager_hunts_the_sheep_of_the_rally_point():
    server, g = setup()
    v = villager(server, g)
    assert v.state == "to_prey" and v.prey == SHEEP and v.res == "food"


def test_a_gone_sheep_sends_the_new_villager_to_the_cell():
    server, g = setup()
    g.prey[SHEEP] = 100
    train.rally(g, TC, (12, 14), SHEEP)
    del g.prey[SHEEP]
    train.queue(g, "Steve", (3, 3))
    v = train.tick(g, train.TRAIN_TIMES["VILLAGER_MALE"])[0]
    assert v.state == "to_rally"
