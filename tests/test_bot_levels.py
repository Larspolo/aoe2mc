"""--ai-difficulty with a comma list: each bot gets its own AI difficulty in seat order (#4020)."""
import pytest
from game import bot, run


class Stop(Exception):
    pass


class FakeGather:
    bots, villagers, units, ended, speed, peers = (), [], [], None, 1.0, []

    def __init__(self, *a, **k):
        pass

    def setup(self):
        pass


def test_a_list_gives_each_bot_its_level_in_seat_order():
    assert [bot.level_of("hard,easy", k) for k in range(2)] == ["hard", "easy"]


def test_the_last_level_serves_the_bots_after_the_list():
    assert [bot.level_of("hard,easy", k) for k in range(4)] == ["hard", "easy", "easy", "easy"]


def test_one_level_serves_every_bot():
    assert [bot.level_of("hard", k) for k in range(3)] == ["hard"] * 3


def test_an_unknown_level_in_the_list_names_the_levels(capsys):
    with pytest.raises(SystemExit):
        run.main(["WORLD", "--play", "--bot", "--ai-difficulty", "hard,insane"])
    err = capsys.readouterr().err
    assert "insane is no level" in err and "easiest, standard, moderate, hard, hardest, extreme" in err


def test_the_two_bots_get_their_own_levels(monkeypatch, tmp_path):
    import bot as bots
    import combat
    import gather as gathers
    from test_play_speed import FakeGame
    seen = []

    class Stub:
        g = type("G", (), {"villagers": []})()

        def setup(self):
            return self

    def bot_of(game, data, **kw):
        seen.append((kw.get("player"), kw.get("difficulty")))
        if len(seen) == 2:
            raise Stop
        return Stub()

    monkeypatch.setattr(bots, "Bot", bot_of)
    monkeypatch.setattr(gathers, "Gather", FakeGather)
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    monkeypatch.setattr(run, "bot_seats", lambda players, people, n: [(2, 1), (3, 1)])
    (tmp_path / "aoe2mc.json").write_text('{"players": {"1": {}, "2": {}, "3": {}}, "tile_size": 4}')
    with pytest.raises(Stop):
        run.play(FakeGame(), str(tmp_path), bot=2, ai_difficulty="hard,easy")
    assert seen == [(2, "hard"), (3, "easy")]
