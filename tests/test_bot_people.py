"""A bot next to two people (#1794): `run.py --play --people 2 --bot` lets the bot play player 3, and it attacks the
first person who is not its ally."""
from game import run


def test_with_one_person_the_bot_plays_player_2_and_attacks_player_1():
    assert run.bot_seat({}, 1) == (2, 1)


def test_with_two_people_the_bot_plays_player_3():
    players = {"1": {"team": 1}, "2": {"team": 1}, "3": {}}
    assert run.bot_seat(players, 2) == (3, 1)


def test_the_bot_attacks_the_first_person_who_is_not_its_ally():
    players = {"1": {"team": 1}, "2": {"team": 2}, "3": {"team": 1}}
    assert run.bot_seat(players, 2) == (3, 2)


def test_the_cli_takes_bot_with_two_people(tmp_path, monkeypatch):
    (tmp_path / "level.dat").write_bytes(b"")
    calls = {}

    class Game:
        def __init__(self, world, version, server):
            self.port = self.game_port = 0

        def start(self):
            pass

        def stop(self):
            pass

    monkeypatch.setattr(run, "Game", Game)
    monkeypatch.setattr(run, "play", lambda game, world, log, cheats, bot, **kw: calls.update(bot=bot, **kw))
    run.main([str(tmp_path), "--play", "--people", "2", "--bot"])
    assert calls["bot"] and calls["people"] == 2
