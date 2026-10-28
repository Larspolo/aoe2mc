"""game/savegame.py: a save keeps the resources that are left on the map (#2453, epic #2253): a half-cut tree, a
half-mined gold mine, a farm, a berry bush, a carcass and a fish keep the amount of the save after a load, and a
resource that was empty at the save stays empty. Fake server, no Minecraft."""
import json

from test_gather import FakeServer, grid

from game import gather, savegame

OBJECTS = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 6, 6]},
           {"kind": "building", "name": "FARM", "player": 1, "tile": [10.5, 10.5], "footprint": [9, 9, 12, 12]},
           {"kind": "other", "name": "TREE_OAK", "tile": [20.5, 4.5]},
           {"kind": "other", "name": "TREE_OAK", "tile": [22.5, 4.5]},
           {"kind": "other", "name": "GOLD_MINE", "tile": [16.5, 16.5]},
           {"kind": "other", "name": "GOLD_MINE", "tile": [20.5, 20.5]},
           {"kind": "other", "name": "FRUIT_BUSH", "tile": [4.5, 20.5]},
           {"kind": "other", "name": "FRUIT_BUSH", "tile": [8.5, 20.5]}]


def game():
    return gather.Gather(FakeServer({}), grid([[64] * 28 for _ in range(28)], OBJECTS), start={}).setup()


def played():
    """Villagers cut, mined, farmed and hunted: amounts below the full ones, a tree, a mine and a bush that are empty."""
    g = game()
    m = g.map
    m.trees[(20, 4)], m.trees[(22, 4)] = 37, 0
    gold = next(r for r in m.mines if (16, 16) in m.mines[r])
    m.mines[gold][(16, 16)], m.mines[gold][(20, 20)] = 412.5, 0
    m.farms[(10, 10)], m.bushes[(4, 20)], m.bushes[(8, 20)] = 91.25, 60, 0
    m.carcasses[(14, 8)], m.rot[(14, 8)], m.herds = 230.0, 0.25, {(14, 8)}
    m.fish[(25, 25)] = 140
    g.crops[(10, 10)], g.trunks[(20, 4)], g.dead["deer"] = 5, 3, (14, 8)
    return g, gold


def loaded(g):
    h = game()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return h


def test_a_loaded_game_has_the_amounts_of_the_save():
    g, gold = played()
    h = loaded(g)
    for f in savegame.MAP:
        assert getattr(h.map, f) == getattr(g.map, f), f
    for f in savegame.LEFT:
        assert getattr(h, f) == getattr(g, f), f
    assert h.map.trees[(20, 4)] == 37 and h.map.mines[gold][(16, 16)] == 412.5 and h.map.farms[(10, 10)] == 91.25


def test_an_empty_mine_and_bush_stay_free_ground_after_a_load():
    g, gold = played()
    full = game()
    spot, bush = full.map.spot((20, 20)), full.map.cells((8, 20))
    assert spot <= full.map.blocked and bush <= full.map.blocked     # a new game: the mine and the bush block
    h = loaded(g)
    assert h.map.trees[(22, 4)] == 0 and h.map.mines[gold][(20, 20)] == 0   # gone stays gone
    assert not (spot | bush) & h.map.blocked and not set(h.map.mine_at) & spot
    assert full.map.spot((16, 16)) <= h.map.blocked                 # the half-mined mine still blocks


def test_a_save_from_before_has_the_full_amounts():
    g, gold = played()
    d = savegame.dump(g)
    for p in d["players"].values():
        del p["map"]
        for f in savegame.LEFT:
            p.pop(f, None)
    h = game()
    savegame.load(h, json.loads(json.dumps(d)))
    assert h.map.trees[(20, 4)] == gather.TREE_WOOD and h.map.mines == game().map.mines
