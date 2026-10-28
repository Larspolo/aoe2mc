"""game/bot.py: the bot gathers wood beyond its base when its base has no tree (#3402)."""
from test_bot_gather import bot_map


def far_trees():
    """bot_map with its trees moved to the middle of the map, nearer to the bot than to player 1."""
    server, me, b = bot_map()
    trees = b.g.map.trees
    for t in list(trees):
        trees[t] = 0
    for t in [(0, 20), (1, 20), (0, 21)]:
        trees[t] = 100
    return server, me, b


def test_an_idle_villager_goes_to_a_tree_beyond_its_base():
    server, me, b = far_trees()
    assert not any(k > 0 for k in b.home(b.g.map.trees).values())   # no tree at the base
    v = next(iter(b.g.villagers.values()))
    assert b.go(v, "wood") and v.tree in {(0, 20), (1, 20), (0, 21)}


def test_the_bot_builds_a_lumber_camp_near_the_far_trees():
    server, me, b = far_trees()
    b.g.stock.update(wood=100)
    b.build()
    site = next((s for s in b.g.sites if s["name"] == "LUMBER_CAMP"), None)
    assert site, [s["name"] for s in b.g.sites]
    x0, x1, z0, z1 = site["footprint"]
    assert abs((x0 + x1) / 2 - 0.5) < 8 and abs((z0 + z1) / 2 - 20.5) < 8


def test_no_tree_nearer_to_the_foe_than_half_the_way():
    server, me, b = far_trees()
    b.g.map.trees[(4, 7)] = 100                                        # next to the town center of player 1
    assert (4, 7) not in {t for t, k in b.sources("wood").items() if k > 0}
