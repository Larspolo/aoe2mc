"""#2900 (epic #2897): the spectators see one sidebar (aoe_spec) with the resources and the population of each player."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import spectator  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402


def game(colors=("blue", "red")):
    """One person (player 1) and one bot (player 2) with their own stocks and population."""
    server = FakeServer({})
    data = grid([[64] * 8 for _ in range(8)])
    data["players"] = {"0": {}, **{str(n): {"color": c} for n, c in enumerate(colors, 1)}}
    g = gather.Gather(server, data)
    bot = gather.Gather(server, data, player=2)
    g.bots = [types.SimpleNamespace(g=bot)]
    g.stock.update(food=200, wood=150, gold=100, stone=50)
    bot.stock.update(food=90, wood=80, gold=70, stone=60)
    g.pop, bot.pop = 4, 7
    return server, g, bot


def scores(server):
    return {c.split()[3]: int(c.split()[5]) for c in server.log if c.startswith("scoreboard players set ")
            and f" {spectator.BOARD} " in c}


def test_a_game_of_a_person_and_a_bot_sets_the_lines_of_both_players():
    server, g, bot = game()
    spectator.tick(g)
    assert scores(server) == {"p1_food": 200, "p1_wood": 150, "p1_gold": 100, "p1_stone": 50, "p1_pop": 4,
                              "p2_food": 90, "p2_wood": 80, "p2_gold": 70, "p2_stone": 60, "p2_pop": 7}
    assert "scoreboard objectives setdisplay sidebar.team.gray aoe_spec" in server.log
    assert 'scoreboard players display name p2_pop aoe_spec "P2 Pop"' in server.log


def test_the_sidebar_of_player_1_does_not_change():
    server, g, bot = game()
    spectator.tick(g)
    assert not [c for c in server.log if g.board in c or "sidebar " in c or c.endswith(" sidebar")
                or "sidebar.team.blue" in c]


def test_a_change_sends_one_command_once_per_second():
    server, g, bot = game()
    spectator.tick(g)
    n = len(server.log)
    bot.stock["gold"] = 75
    spectator.tick(g)
    assert len(server.log) == n                                        # in the same second
    g.spectator_at = 0.0
    spectator.tick(g)
    assert server.log[n:] == ["scoreboard players set p2_gold aoe_spec 75"]


def test_a_gray_player_keeps_its_sidebar():
    server, g, bot = game(colors=("blue", "gray"))
    spectator.tick(g)
    assert not [c for c in server.log if "setdisplay sidebar.team.gray aoe_spec" in c]
