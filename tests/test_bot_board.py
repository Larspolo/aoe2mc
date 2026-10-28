"""#2833: the scoreboard objective of a bot holds its start resources, as the objective of player 1 does."""
from test_gather import FakeServer, grid

from game import bot, gather


def test_setup_sets_the_start_resources_on_the_board_of_the_bot():
    server = FakeServer({})
    b = bot.Bot(server, grid([[64] * 8 for _ in range(8)], []), resources="high").setup()
    assert b.g.board == "aoe_res2"
    for r in gather.RESOURCES:
        assert f"scoreboard players set {r} aoe_res2 {gather.LEVELS['high'][r.lower()]}" in server.log, r
    assert server.log.index('scoreboard objectives add aoe_res2 dummy "Player 2"') < \
        server.log.index(f"scoreboard players set Food aoe_res2 {gather.LEVELS['high']['food']}")
