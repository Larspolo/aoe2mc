"""#2542 (epic #2538): a scenario trigger with the effect "Declare Victory" ends a game of the scenario mode. The
converter sets the score #p<N> of aoe_win, and scenario.victory reads it."""
import os
import sys
import types
from collections import Counter

import numpy as np

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import scenario  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402


def victory(player=1, timer=30):
    e = dict(type=aoe2mc.DECLARE_VICTORY, message="", player=player, time=0, object=None, tile=[-1, -1],
             area=[-1, -1, -1, -1])
    return dict(id=4, name="Win", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=timer, inverted=False)], effects=[e])


def test_the_trigger_function_sets_the_score_of_its_player():
    stats = Counter()
    load, files = aoe2mc.trigger_files([victory(2)], 4, np.full((16, 16), 64, np.int16), {}, stats)
    assert files["data/aoe2mc/function/trigger/4.mcfunction"] == "scoreboard players set #p2 aoe_win 1\n"
    assert load == ["scoreboard objectives add aoe_win dummy", "schedule function aoe2mc:trigger/4 600t replace"]
    assert stats == Counter({"declare victory": 1})


def test_no_victory_effect_makes_no_objective():
    t = dict(victory(), effects=[dict(type=aoe2mc.SEND_CHAT, message="Hi", player=1, time=0)])
    load, _ = aoe2mc.trigger_files([t], 4, np.full((16, 16), 64, np.int16), {})
    assert "scoreboard objectives add aoe_win dummy" not in load


class Server(FakeServer):
    def __init__(self, wins):
        super().__init__({})
        self.wins = wins

    def command(self, cmd):
        if cmd.startswith("scoreboard players get #p") and cmd.endswith(" aoe_win"):
            self.log.append(cmd)
            n = int(cmd.split()[3][2:])
            return f"#p{n} has {self.wins[n]} [aoe_win]" if n in self.wins else \
                f"Can't get value of aoe_win for #p{n}; none is set"
        return super().command(cmd)


def game(wins, teams=None):
    server = Server(wins)
    data = grid([[64] * 16 for _ in range(16)], [])
    data["players"] = {"0": {}, **{str(n): {"team": t} if t else {} for n, t in (teams or {1: None, 2: None}).items()}}
    g = gather.Gather(server, data).setup()
    g.bots = [types.SimpleNamespace(g=gather.Gather(server, data, player=2).setup())]
    return server, g, g.bots[0].g


def titles(server):
    return [c for c in server.log if c.startswith("title @a[team=")]


def test_the_score_1_of_player_1_gives_victory_and_ends_the_game():
    server, g, bot = game({1: 1})
    scenario.victory(g)
    assert g.ended == "Victory" and bot.ended == "Defeat"
    assert 'title @a[team=p1] title {"translate":"aoe2mc.victory","fallback":"Victory","color":"gold"}' in titles(server)


def test_a_victory_of_player_2_is_a_defeat_of_player_1():
    _, g, bot = game({2: 1})
    scenario.victory(g)
    assert g.ended == "Defeat" and bot.ended == "Victory"


def test_allies_win_together():
    _, g, bot = game({2: 1}, {1: 1, 2: 1})
    scenario.victory(g)
    assert g.ended == bot.ended == "Victory"


def test_a_world_without_the_effect_never_ends_by_this_rule():
    server, g, bot = game({})
    for _ in range(3):
        g.win_at = 0.0
        scenario.victory(g)
    assert not g.ended and not bot.ended and not titles(server)
    assert server.log.count("scoreboard players get #p1 aoe_win") == 3
