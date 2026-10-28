"""A saved game of the game program keeps the train and research queues, the construction sites and the rally points
(#2257, epic #2253): after a load a queue goes on at its progress, a site keeps its built part, and a building keeps
its rally point."""
import json

from test_loom import setup

from game import savegame, train


def played():
    """A town center with 2 villagers in its queue (the first at half its time) and Loom behind them, a house site at
    40 % and a rally point."""
    server, g = setup(food=500, gold=500)
    g.stock["wood"] = 500
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, train.ITEMS["VILLAGER_MALE"][0], shift=False) == 1
    assert train.order(g, "Steve", rect, train.ITEMS["VILLAGER_MALE"][0], shift=False) == 1
    assert train.order(g, "Steve", rect, train.ITEMS["LOOM"][0], shift=False) == 1
    g.queues[rect][0]["progress"] = 0.5
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": (8, 10, 8, 10), "sent": 3, "progress": 0.4,   # build.found
                    "commands": ["setblock 8 64 8 minecraft:oak_planks"] * 5,
                    "ring": {(8, 64, 8): "minecraft:blue_wool"}, "under": {(9, 64, 9): "minecraft:water"}})
    train.rally(g, rect, (6, 7))
    return g, rect


def test_a_loaded_game_has_the_queues_sites_and_rally_points():
    g, rect = played()
    text = json.dumps(savegame.dump(g), sort_keys=True)
    _, h = setup()
    savegame.load(h, json.loads(text))
    assert h.queues == g.queues and [e["name"] for e in h.queues[rect]] == ["VILLAGER_MALE", "VILLAGER_MALE", "LOOM"]
    assert h.queues[rect][0]["progress"] == 0.5
    assert h.sites == g.sites and h.sites[0]["progress"] == 0.4 and h.sites[0]["footprint"] == (8, 10, 8, 10)
    assert h.rally == g.rally and h.rally[rect][0] == (6, 7)
    assert h.trained == g.trained


def test_the_queue_goes_on_after_the_load():
    g, rect = played()
    _, h = setup()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g))))
    for x in (g, h):
        train.tick(x, 1)
    assert h.queues[rect][0]["progress"] == g.queues[rect][0]["progress"] > 0.5


def test_pack_turns_back_tuples_and_tuple_keys():
    v = {(1, 2, 3, 4): [{"cell": (5, 6), "ring": {(1, 64, 2): "minecraft:red_wool"}}], "n": 1.5}
    assert savegame.unpack(json.loads(json.dumps(savegame.pack(v)))) == v


def test_a_save_without_queues_still_loads():
    g, _ = played()
    d = savegame.dump(g)
    for f in savegame.PACKED:
        del d["players"]["1"][f]
    _, h = setup()
    savegame.load(h, d)
    assert h.queues == {} and h.stock == g.stock
