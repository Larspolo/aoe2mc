"""A saved game keeps the owner changes (#2999): a converted unit and building, a captured sheep, a unit of the game."""
import json

from test_gather import FakeServer, grid

from game import combat, gather, herd, owners, savegame, train

BARRACKS = [10, 10, 13, 13]


def game():
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "BARRACKS", "player": 2, "tile": [11.5, 11.5], "footprint": BARRACKS},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]},
               {"kind": "unit", "name": "MAN_AT_ARMS", "player": 2, "uuid": "maa2", "tile": [8.5, 8.5]},
               {"kind": "unit", "name": "SHEEP", "player": 0, "uuid": "sheep", "tile": [6.5, 6.5]}]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}, "maa2": {"Pos": (8.5, 64.0, 8.5)},
                         "sheep": {"Pos": (6.5, 64.0, 6.5)}})
    return gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()


def test_a_loaded_game_keeps_the_owners():
    g, barracks = game(), combat.target_uuid(BARRACKS)
    owners.give(g, "maa2", 1)                                          # monk.take
    owners.give_building(g, barracks, 1)                               # monk.win
    next(o for o in g.data["objects"] if o["name"] == "BARRACKS")["player"] = 1
    herd.take(g, [g], next(o for o in g.data["objects"] if o.get("uuid") == "sheep"), 1)
    owners.add(g, "mil2", "MILITIA", 2)                                # trained by the bot of player 2
    assert "maa2" not in g.enemies and barracks not in g.forts
    d = json.loads(json.dumps(savegame.dump(g), sort_keys=True))
    h = game()
    savegame.load(h, d)
    assert "maa2" in h.soldiers and "maa2" not in h.enemies
    assert (10, 13, 10, 13) in train.homes(h) and barracks not in h.forts
    assert "sheep" in h.flock and "sheep" in h.prey
    assert h.enemies.get("mil2") == "MILITIA"


def test_a_save_before_the_owner_record_loads_as_before():
    g = game()
    owners.give(g, "maa2", 1)
    d = json.loads(json.dumps(savegame.dump(g), sort_keys=True))
    del d["owners"]
    h = game()
    savegame.load(h, d)
    assert "maa2" in h.enemies and combat.target_uuid(BARRACKS) in h.forts
