"""game/cheats.py: "sharing is caring" sends the income of the player to its allies in equal parts (#969)."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_cheat_end import cheat, game  # noqa: E402
from test_gather import tiny  # noqa: E402

from game import bot, gather  # noqa: E402


def setup(teams, on=True):
    """Player 1 with the bots of players 2 and 3; teams: {player: team} of aoe2mc.json."""
    server, g = game(on)
    g.players.update({str(p): {"team": t} for p, t in teams.items()})
    g.bots = [bot.Bot(server, g.data, player=p, share=g).setup() for p in (2, 3)]
    for h in (g, *(b.g for b in g.bots)):
        h.stock.update(dict.fromkeys(h.stock, 0))                      # no start resources: the income only
    return server, g, *(b.g for b in g.bots)


def test_the_wood_of_the_player_goes_to_the_ally():
    server, g, ally, foe = setup({1: 1, 2: 1, 3: 2})
    log = cheat(server, g, "sharing is caring")
    assert 'tellraw Steve {"text":"Sharing is caring: your income goes to your allies"}' in log
    server.log.clear()
    g.earn("wood", 10)
    assert g.stock["wood"] == 0 and ally.stock["wood"] == 10 and foe.stock["wood"] == 0
    assert server.log == ["scoreboard players add Wood aoe_res2 10"]       # the board of the ally bot


def test_two_allies_share_in_equal_parts():
    server, g, a, b = setup({1: 1, 2: 1, 3: 1})
    cheat(server, g, "sharing is caring")
    g.earn("gold", 7)
    assert (g.stock["gold"], a.stock["gold"], b.stock["gold"]) == (0, 4, 3)


def test_without_ally_or_cheat_the_player_keeps_the_income():
    server, g, *_ = setup({1: 1, 2: 2, 3: 3})
    cheat(server, g, "sharing is caring")
    g.earn("food", 5)
    assert g.stock["food"] == 5
    server, g, ally, _ = setup({1: 1, 2: 1, 3: 2}, on=False)
    cheat(server, g, "sharing is caring")                                 # cheats off: the code is chat
    assert not g.sharing
    g.earn("wood", 10)
    assert g.stock["wood"] == 10 and ally.stock["wood"] == 0


def test_the_wood_that_a_villager_drops_goes_to_the_ally(tiny_world):
    data, uuid, server, g = tiny(tiny_world)
    data["players"] = g.players = {"1": {"team": 1}, "2": {"team": 1}}
    ally = gather.Gather(server, data, player=2, start={})
    g.bots, g.sharing = [SimpleNamespace(g=ally)], True
    g.select(uuid)
    g.send(*g.map.trees)
    for _ in range(400):
        g.step()
    assert g.stock["wood"] == 0 and ally.stock["wood"] >= 6 == server.wood() - ally.stock["wood"] + 6
