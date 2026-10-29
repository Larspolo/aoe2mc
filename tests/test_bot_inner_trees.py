"""game/bot.py: a bot villager next to a forest behind a row of houses goes to a tree with a free cell next to it (#3726).
Bot.go took the nearest tree by its middle: an inner tree of a forest has no free cell (Gather.goals is empty), so the
villager stopped at once, and the next order took the next inner tree, one tree per tick."""
from test_gather import FakeServer, grid

from game import bot, gather


def forest_map():
    """A flat 48 × 48 map (tile size 1): a town center and a villager of player 2 west of a row of houses (x = 8, 9) and,
    behind them, a forest of 30 × 22 trees (x = 10 to 39, z = 14 to 35). Only the trees of the north and south rows and of
    the east column have a free cell next to them; about 180 inner trees are nearer to the villager by their middle."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [44, 44, 47, 47]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 2, "footprint": [1, 20, 4, 23]},
               {"kind": "unit", "name": "VILLAGER_FEMALE", "player": 2, "uuid": "b0", "tile": [6.5, 24.5]}]
    objects += [{"kind": "building", "name": "HOUSE", "player": 2, "footprint": [8, z, 10, z + 2]} for z in range(14, 36, 2)]
    objects += [{"kind": "other", "name": "TREE_OAK", "tile": [x + 0.5, z + 0.5]} for x in range(10, 40) for z in range(14, 36)]
    server = FakeServer({"b0": {"Pos": (6.5, 64.0, 24.5)}})
    data = grid([[64] * 48 for _ in range(48)], objects)
    data.update(level_height=1, players={"2": {"color": "blue", "arch": "western"}})
    me = gather.Gather(server, data, carry=10, chop=0.05, start={}).setup()
    return bot.Bot(server, data, share=me, carry=10, chop=0.05, start={}).setup()


def test_the_villager_chops_a_reachable_tree_within_15_game_seconds():
    b = forest_map()
    v = b.g.villagers["b0"]
    inner = [t for t in b.g.map.trees if not b.g.goals(t)]
    assert len(inner) > 150
    while v.state != "chop" and b.time < 15:
        b.step()
    assert v.state == "chop" and b.g.goals(v.tree), (b.time, v.state, v.tree)
    assert not b.failed.keys() & inner                                 # it never tried an inner tree


def test_go_skips_a_source_with_no_free_cell():
    b = forest_map()
    v = b.g.villagers["b0"]
    assert b.go(v, "wood")
    assert v.tree in b.g.map.trees and b.g.goals(v.tree) and v.state == "to_tree" and v.path
    for t in list(b.g.map.trees):                                      # only inner trees are left
        if b.g.goals(t):
            b.g.map.trees[t] = 0
    assert not b.go(v, "wood")                                         # no source to walk to: the next resource
