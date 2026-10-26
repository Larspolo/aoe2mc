"""game/train.py census: a dead villager leaves Gather.villagers, the selection, its farm and the idle count (#1039).
Fake server of test_gather, the map of test_train_population."""
from test_train_population import setup

from game import gather, train


def test_a_dead_villager_leaves_the_list_and_the_idle_count():
    server, g = setup()
    server.entities["w"] = {"Pos": (8.5, 64.0, 8.5)}
    g.villagers["w"] = gather.Villager("w", (8.5, 64.0, 8.5))
    g.selected, g.farmers = {"v", "w"}, {(5, 5): "w"}
    train.census(g)
    g.idle()
    assert g.pop == 2 and "scoreboard players set Idle aoe_res 2" in server.log
    del server.entities["w"]                                           # killed: no position
    train.census(g)
    g.idle()
    assert set(g.villagers) == {"v"} and g.selected == {"v"} and g.farmers == {} and g.pop == 1
    assert server.log[-1] == "scoreboard players set Idle aoe_res 1"
