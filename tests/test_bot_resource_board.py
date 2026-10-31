"""#3090: the resources of a bot go to the objective that the triggers read for its player (aoe_res<N>)."""
from test_gather import FakeServer, grid

import aoe2mc
from game import bot, gather


def test_the_board_of_a_bot_is_the_objective_of_its_resource_score():
    server = FakeServer({})
    b = bot.Bot(server, grid([[64] * 8 for _ in range(8)], []), player=2).setup()
    assert b.g.board == "aoe_res2"
    assert aoe2mc.resource_score({"attribute": 0, "player": 2, "quantity": 500}) == "score Food aoe_res2 matches 500.."


def test_the_start_resources_of_a_bot_go_to_its_board():
    server = FakeServer({})
    bot.Bot(server, grid([[64] * 8 for _ in range(8)], []), resources="high").setup()
    for r in gather.RESOURCES:
        assert f"scoreboard players set {r} aoe_res2 {gather.LEVELS['high'][r.lower()]}" in server.log, r


def test_the_setup_of_a_bot_shows_no_sidebar():
    server = FakeServer({})
    bot.Bot(server, grid([[64] * 8 for _ in range(8)], []), player=2).setup()
    assert not any("setdisplay" in c for c in server.log)
