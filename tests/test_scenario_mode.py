"""#2540 (epic #2538): `run.py --play --mode scenario` starts each player with the start resources and the population
limit of the scenario (aoe2mc.json "players", #2539), not with the lobby settings."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import run  # noqa: E402
import scenario  # noqa: E402
import train  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402

START = {"food": 500, "wood": 400, "gold": 300, "stone": 200}


def game(players):
    server = FakeServer({})
    data = grid([[64] * 16 for _ in range(16)], [])
    data["players"] = players
    g = gather.Gather(server, data).setup()
    bot = gather.Gather(server, data, player=2).setup()
    g.bots = [types.SimpleNamespace(g=bot)]
    return server, g, bot


def test_each_player_starts_with_the_scenario_values():
    server, g, bot = game({"0": {}, "1": {"resources": START, "pop_limit": 75},
                           "2": {"resources": dict(START, food=50), "pop_limit": 125}})
    scenario.setup(g, "scenario")
    assert g.stock == START and train.max_pop(g) == 75
    assert bot.stock["food"] == 50 and train.max_pop(bot) == 125
    assert f"scoreboard players set Food {g.board} 500" in server.log


def test_a_world_without_scenario_values_keeps_the_lobby_values(capsys):
    _, g, bot = game({"0": {}, "1": {"color": "blue"}, "2": {"color": "red"}})
    before, limit = dict(g.stock), train.max_pop(g)
    scenario.setup(g, "scenario")
    assert g.stock == before and train.max_pop(g) == limit and bot.stock == before
    assert "lobby settings" in capsys.readouterr().err


def test_the_mode_shows_in_the_help(capsys):
    try:
        run.main(["--help"])
    except SystemExit:
        pass
    assert "scenario: each player starts with the resources" in " ".join(capsys.readouterr().out.split())
