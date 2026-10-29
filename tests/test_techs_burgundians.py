"""Unique technology of the Burgundians (#4323): the castle of the Burgundians researches Flemish Revolution in the
Imperial Age. It costs more for each own villager (the key "per_own"), and the own villagers become Flemish Militia
(the key "on_research": cheats.flemish, the transformation of the cheat)."""
from test_gather import FakeServer, grid
from test_train_castle import menus, setup

from game import build, gather, train

CASTLE = (12, 4)
TECH = next(n for n, h in train.BY_KEY["on_research"].items() if "cheats.flemish" in h)


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def village():
    """The map of setup(): 3 villagers of player 1 ("a", "b", "c") and one of player 2 ("d")."""
    tiles = {"a": (5.5, 9.5), "b": (6.5, 9.5), "c": (7.5, 9.5), "d": (20.5, 20.5)}
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "CASTLE", "player": 1, "tile": [12.0, 4.0], "footprint": [10, 2, 14, 6]}]
    objects += [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1 + (u == "d"), "uuid": u, "tile": list(t)}
                for u, t in tiles.items()]
    data = grid([[64] * 24 for _ in range(24)], objects) | {"players": {"1": {"civ": "BURGUNDIANS", "color": "blue"},
                                                                       "2": {"civ": "BRITONS", "color": "red"}}}
    entities = {u: {"Pos": (x, 64.0, z)} for u, (x, z) in tiles.items()}
    server = FakeServer({"Steve": {"Pos": (12.0, 64.0, 9.5), "Rotation": (180, 15)}} | entities)
    g = gather.Gather(server, data, start={}).setup()
    g.stock.update(food=5000, wood=5000, gold=5000)
    g.techs.update(build.AGE_TECHS[:3])
    return server, g


def test_only_the_castle_of_the_burgundians_researches_flemish_revolution():
    server, g = setup("BURGUNDIANS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, TECH)}:" in menus(server)[-1]
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, TECH) is None


def test_flemish_revolution_costs_more_for_each_own_villager():
    server, g = village()
    kinds, more = train.BY_KEY["per_own"][TECH]
    assert train.per_enemy(g, TECH) == {r: train.COSTS[TECH].get(r, 0) + 3 * more.get(r, 0)
                                        for r in train.COSTS[TECH] | more}


def test_flemish_revolution_turns_the_own_villagers_into_flemish_militia():
    server, g = village()
    assert {"a", "b", "c"} <= set(g.villagers)
    assert train.queue(g, "Steve", CASTLE, TECH)
    train.tick(g, train.seconds(g, TECH, "CASTLE"))
    assert TECH in g.techs
    assert sorted(g.soldiers.values()).count("FLEMISH_MILITIA") == 3
    assert not {"a", "b", "c"} & set(g.villagers)
    assert "kill d" not in server.log                                  # a villager of another player stays
