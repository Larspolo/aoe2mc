"""The map, player, random and time functions of an XS script (game/xs_host.py, #5839)."""
from tests.test_xs_host import side, value


def world():
    g = side()
    g.data = {"map_size": 3, "objects": [], "lobby": {"scenario": "duel.aoe2scenario"},
              "players": {"1": {"civ": "BRITONS", "name": "Ann"}, "2": {"civ": "FRANKS"}},
              "terrain": ["0 1 2", "3 4 5", "6 7 8"], "elevation": ["0 0 0", "0 2 0", "0 0 0"]}
    return g


def test_map():
    g = world()
    assert value(g, "xsGetMapWidth() * 10 + xsGetMapHeight()") == 33
    assert value(g, "xsGetMapTileAttribute(2, 1, 0)") == 5
    assert value(g, "xsGetMapTileAttribute(1, 1, 1)") == 2
    assert value(g, "xsGetMapTileAttribute(9, 1, 0)") == -1
    assert value(g, "xsGetMapName()", "string") == "duel"
    assert value(g, "xsGetMapName(true)", "string") == "duel.aoe2scenario"
    assert value(g, "xsGetMapSeed()") == value(world(), "xsGetMapSeed()")


def test_players_and_the_context_player():
    g = world()
    assert value(g, "xsGetNumPlayers()") == 3
    assert value(g, "xsGetPlayerName(1)", "string") == "Ann"
    assert value(g, "xsGetPlayerName(2)", "string") == "Player 2"
    assert value(g, "xsGetContextPlayer()") == 1
    assert value(g, "xsGetPlayerInGame(1)", "bool") and not value(g, "xsGetPlayerInGame(5)", "bool")
    assert value(g, "xsGetWorldPlayerId(2)") == 2
    assert value(g, "xsGetHandicapMultiplier(1)", "float") == 1.0
    assert value(g, "0; xsSetContextPlayer(2); r = xsGetContextPlayer()") == 2
    assert value(g, "xsGetPlayerNumberOfTechs(-1)") == 2


def test_random_numbers_are_in_range_and_deterministic():
    script = "xsGetRandomNumberLH(5, 8) * 100000 + xsGetRandomNumberMax(3) * 10000 + xsGetRandomNumber() % 10000"
    a = value(world(), script)
    assert a == value(world(), script)
    assert 5 <= a // 100000 < 8 and (a // 10000) % 10 < 3


def test_times():
    g = world()
    t = value(g, "xsGetWorldTime()")
    assert t > 0 and value(g, "xsGetTurn()") > 0 and value(g, "xsGetGameTime()") == t // 1000
