"""The bot gathers at its own base (#1810): no villager goes to a source nearer to a building of the foe than to an
own town center or drop site, and the bot builds farms when its own bushes are empty."""
from test_bot_gather import bot_map

FOE_BUSH = (4, 7)                                                     # 2 tiles from the town center of player 1
OWN_BUSH = (21, 26)


def demo():
    """The demo of #1810: the bush of the bot is empty, player 1 has a full bush next to its town center."""
    server, me, b = bot_map()
    me.map.bushes[OWN_BUSH] = 0
    me.map.bushes[FOE_BUSH] = 125
    return server, me, b


def test_the_sources_are_only_the_ones_at_home():
    _, me, b = demo()
    me.map.bushes[OWN_BUSH] = 125
    assert set(b.sources("food")) == {OWN_BUSH}
    assert set(b.sources("wood")) == set(me.map.trees)                 # the trees are near the bot


def test_no_bot_villager_goes_to_the_bush_of_the_foe():
    _, _, b = demo()
    for _ in range(600):
        b.step()
        assert all(v.tree != FOE_BUSH for v in b.g.villagers.values())
    assert any(v.res == "food" for v in b.g.villagers.values()) or b.g.sites   # the food share waits for a farm


def test_the_bot_builds_a_farm_when_its_bushes_are_empty():
    _, me, b = demo()
    b.g.stock.update(wood=1000, food=1000)
    for _ in range(600):
        me.map.bushes[FOE_BUSH] = 125                                  # the bush of the foe stays full
        b.step()
        if any(s["name"] == "FARM" for s in b.g.sites):
            break
    assert any(s["name"] == "FARM" for s in b.g.sites), [s["name"] for s in b.g.sites]


def test_the_next_bush_of_an_empty_one_is_at_home():
    """Gather.nearest (AoE2: a forager goes on to the nearest bush) takes no bush of the foe either."""
    _, me, b = demo()
    v = next(iter(b.g.villagers.values()))
    v.res, v.tree = "food", OWN_BUSH
    assert b.g.nearest(v) is None                                      # the bush of the foe is not a candidate
    assert me.nearest(v) == FOE_BUSH                                   # player 1 takes it
