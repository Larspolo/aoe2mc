"""A save and a load of a game with several bots keep the foe and the difficulty of each bot (#4022)."""
import pytest
from test_bot_gather import bot_map

from game import bot, savegame


def game(levels, foes):
    """The game of bot_map with a bot for players 2 to 4 of the given levels and foes."""
    server, me, _ = bot_map()
    me.bots = [bot.Bot(server, me.data, player=p, share=me, foe=f, difficulty=d, carry=10, chop=0.05, start={})
               for p, d, f in zip((2, 3, 4), levels, foes)]
    return me


def test_each_bot_keeps_its_player_foe_and_difficulty():
    me = game(("easiest", "hard", "hardest"), (1, 4, 3))
    me.bots[1].foe = 2                                                 # a foe change in the game (#4019)
    state = savegame.dump(me)
    new = game(("standard",) * 3, (1, 1, 1))
    savegame.bots_again(new, state)
    assert [(b.g.player, b.foe, b.difficulty) for b in new.bots] == [(2, 1, "easiest"), (3, 2, "hard"), (4, 3, "hardest")]
    assert [b.g.chop for b in new.bots] == [pytest.approx(b.g.chop) for b in me.bots]   # the work rate of the saved level
