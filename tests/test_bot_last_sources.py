"""game/bot.py: the bot gathers near the foe when no source is left at its base or beyond it (#3545)."""
from test_bot_gather import bot_map


def test_the_bot_sends_a_villager_to_the_only_tree_near_the_foe():
    server, me, b = bot_map()
    trees = b.g.map.trees
    for t in list(trees):
        trees[t] = 0
    trees[(4, 7)] = 100                                                # next to the town center of player 1
    v = next(iter(b.g.villagers.values()))
    assert b.go(v, "wood") and v.tree == (4, 7)
