"""#5893: a bot plays for a person who left a network game until the person joins again. The log thread (Game.op_joined)
only queues the leave and the join; the game loop (rejoin.tick) adds and removes the bot."""
import types

import bot
import pytest
import rejoin
import run

PLAYERS = {"1": {}, "2": {}}


def fake_game(wait=False):
    """A Game with a fake server log: op_joined reads it, the commands go into a list."""
    game = run.Game.__new__(run.Game)
    game.server, game.seen, game.sent = types.SimpleNamespace(log=[]), 0, []
    game.command = game.sent.append
    game.sides, game.people, game.kind, game.wait = {}, 2, "vanilla", wait
    game.drops, game.left = run.collections.deque(), frozenset()
    return game


def log(game, *lines):
    game.server.log += [f"[10:00:00] [Server thread/INFO]: {line}" for line in lines]
    game.op_joined()


def gather(game, player):
    return types.SimpleNamespace(game=game, player=player, data={"players": PLAYERS}, chop={"wood": 2.0},
                                 stock={"food": 120, "wood": 75}, villagers={"v1": object()}, bots=[])


@pytest.fixture
def orders(monkeypatch):
    calls = []
    monkeypatch.setattr(bot.Bot, "orders", lambda b: calls.append(b.g.player))
    return calls


def setup_game(wait=False):
    game = fake_game(wait)
    g = gather(game, 1)
    second = gather(game, 2)
    g.bots = [run.Side(second)]
    log(game, "Alex joined the game", "Bob joined the game")
    return game, g, second


def texts(game):
    return [c for c in game.sent if c.startswith("tellraw @a ")]


def test_a_leave_after_the_start_adds_a_bot_and_the_join_removes_it(orders):
    game, g, second = setup_game()
    assert game.sides == {"Alex": 1, "Bob": 2}
    stock, villagers, chop = dict(second.stock), dict(second.villagers), second.chop
    rejoin.tick(g)
    assert vars(g).get("stand_ins", {}) == {}                   # a first join adds no bot
    log(game, "Bob left the game")
    assert vars(g).get("stand_ins", {}) == {}                   # the log thread only queues the leave
    rejoin.tick(g)
    assert list(g.stand_ins) == [2] and g.stand_ins[2].g is second and g.stand_ins[2].own
    assert orders == [2]                                        # the game loop gives its orders
    assert rejoin.LEFT_KEY in texts(game)[-1] and '"Bob"' in texts(game)[-1]
    rejoin.tick(g)
    assert len(g.stand_ins) == 1                                # one bot, also after more steps
    log(game, "Bob joined the game")
    rejoin.tick(g)
    assert g.stand_ins == {} and orders == [2, 2]
    assert game.sides["Bob"] == 2 and "team join p2 Bob" in game.sent[-3:]
    assert second.stock == stock and second.villagers == villagers and second.chop is chop
    assert "home" not in vars(second) and "work_on" not in vars(second)   # the person gives the tasks again
    assert rejoin.BACK_KEY in texts(game)[-1]


def test_the_person_of_player_1_gets_a_bot_too(orders):
    game, g, _ = setup_game()
    log(game, "Alex left the game")
    rejoin.tick(g)
    assert list(g.stand_ins) == [1] and g.stand_ins[1].g is g and g.stand_ins[1].foe == 2


def test_a_leave_before_the_start_only_frees_the_seat(orders):
    game, g, _ = setup_game(wait=True)
    game.ready = {"Alex", "Bob"}
    log(game, "Bob left the game")
    rejoin.tick(g)
    assert vars(g).get("stand_ins", {}) == {} and not game.drops
    assert game.sides == {"Alex": 1} and game.ready == {"Alex"} and game.joined == {"Alex"}
    log(game, "Carl joined the game")
    assert game.sides["Carl"] == 2                              # the free seat


def test_a_coop_partner_online_plays_on_without_a_bot(orders):
    game, g, _ = setup_game()
    game.sides["Cleo"], game.joined = 2, {*game.joined, "Cleo"}
    log(game, "Bob left the game")
    rejoin.tick(g)
    assert vars(g).get("stand_ins", {}) == {}
    log(game, "Cleo left the game")
    rejoin.tick(g)
    assert list(g.stand_ins) == [2]
    log(game, "Bob joined the game")
    rejoin.tick(g)
    assert g.stand_ins == {}


def test_a_leave_line_in_its_own_color_counts():
    line = "[02:38:14 INFO]: System chat: \x1b[94mAlex\x1b[93m left the game\x1b[0m"
    assert run.LEFT.search(line).group(1) == "Alex"
    assert not run.JOINED.search(line) and not run.LEFT.search("[02:38:14 INFO]: <Bob> Alex left the game")
