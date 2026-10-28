"""game/savegame.py: a save keeps the orders of the units (#2258, epic #2253): the job, target and load of each
villager, the farmers, the stances, the control groups and the garrisons. Fake server, no Minecraft."""
import json

from test_gather_farms import farm_map

from game import savegame

UNITS = ("lumberjack", "farmer", "inside", "a", "b")


def played():
    """A lumberjack that carries 6 wood to the town center, a farmer on its farm, a villager in the town center, a
    unit on stand ground and a control group of 3 units."""
    server, g = farm_map(UNITS)
    v = g.villagers["lumberjack"]
    v.res, v.tree, v.load = "wood", (20, 20), 6
    g.go(v, "to_drop", g.drop_goals(v))
    f = g.villagers["farmer"]
    f.res, f.tree, f.state, f.load, f.lap = "food", (10, 10), "chop", 3, 2
    g.farmers[(10, 10)] = "farmer"
    g.garrisons[(2, 5, 2, 5)] = ["inside"]
    g.villagers["inside"].pos = (3.5, 64.0, 3.5)
    g.stances["a"] = "stand_ground"
    g.groups[1] = {"a", "b", "lumberjack"}
    return g


def loaded(g):
    _, h = farm_map(UNITS)
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return h


def test_a_loaded_game_has_the_saved_orders():
    g = played()
    h = loaded(g)
    for u in UNITS:
        a, b = g.villagers[u], h.villagers[u]
        assert [getattr(b, f) for f in (*savegame.JOB, "pos", "tree")] == [getattr(a, f) for f in (*savegame.JOB, "pos", "tree")], u
    assert h.villagers["lumberjack"].load == 6 and h.villagers["lumberjack"].state == "to_drop"
    assert h.farmers == {(10, 10): "farmer"} and h.villagers["farmer"].state == "chop"
    assert h.stances == {"a": "stand_ground"} and h.groups == {1: {"a", "b", "lumberjack"}}
    assert h.garrisons == {(2, 5, 2, 5): ["inside"]}


def test_the_lumberjack_walks_again_and_drops_its_wood():
    h = loaded(played())
    v = h.villagers["lumberjack"]
    assert v.path                                                      # a new path to the town center
    for _ in range(200):
        h.step()
        if h.stock["wood"]:
            break
    assert h.stock["wood"] == 6 and v.load == 0


def test_a_villager_trained_in_the_game_comes_back():
    g = played()
    g.villagers["lumberjack"].uuid = "new"
    g.villagers["new"] = g.villagers.pop("lumberjack")
    h = loaded(g)
    assert h.villagers["new"].load == 6 and h.villagers["new"].pos == g.villagers["new"].pos


def test_a_builder_of_a_site_that_the_save_does_not_have_is_idle():
    g = played()
    g.villagers["b"].state, g.villagers["b"].site = "build", {"footprint": [14, 18, 14, 18]}
    assert loaded(g).villagers["b"].state == "idle"


def test_a_save_from_before_the_orders_still_loads():
    g = played()
    d = savegame.dump(g)
    for k in savegame.orders(g):
        del d["players"]["1"][k]
    _, h = farm_map(UNITS)
    savegame.load(h, d)
    assert h.stock == g.stock and h.villagers["lumberjack"].load == 0
