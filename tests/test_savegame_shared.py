"""game/savegame.py: after a load, the human player and the bot still share the trees, bushes and mines of the map
(the bot takes the same dicts of the human player, bot.Bot.__init__). Fake server, no Minecraft."""
import json

from test_bot_gather import bot_map
from test_savegame_map import game

from game import run, savegame


def loaded():
    """The save of player 1 of a game with a bot, loaded into a new game with a bot."""
    _, me, _ = bot_map()
    d = json.loads(json.dumps(savegame.dump(me), sort_keys=True))
    _, me2, b2 = bot_map()
    savegame.load(me2, d)
    return me2, b2


def test_a_loaded_game_shares_the_trees_bushes_and_mines_with_the_bot():
    me, b = loaded()
    for f in ("trees", "bushes", "mines"):
        assert getattr(b.g.map, f) is getattr(me.map, f), f


def test_the_bot_gets_no_wood_from_a_tree_that_the_human_player_emptied():
    me, b = loaded()
    me.map.trees[(26, 21)] = 0
    me.map.trees[(27, 21)] = 0
    assert b.g.map.trees[(26, 21)] == 0 and b.g.map.trees[(27, 21)] == 0


def two_people():
    """The Gather of player 1 and the Side of a second person, which share the map as run.play joins them."""
    g, h = game(), game()
    h.player = 2
    g.bots = [run.Side(h)]
    h.map.trees, h.map.bushes, h.map.mines = g.map.trees, g.map.bushes, g.map.mines
    return g, h


def test_a_second_person_shares_the_trees_bushes_and_mines_after_a_load():
    src, _ = two_people()
    d = json.loads(json.dumps(savegame.dump(src), sort_keys=True))
    g, h = two_people()
    savegame.load(g, d)
    for f in ("trees", "bushes", "mines"):
        assert getattr(h.map, f) is getattr(g.map, f), f
    g.map.trees[(20, 4)] = 0
    assert h.map.trees[(20, 4)] == 0
