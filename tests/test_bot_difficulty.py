"""The AoE2 DE setting "AI difficulty" of the bot (#2661, decision #2648 option A): the levels by numbers in
game/data/difficulty.jsonl (bot.LEVELS): the gather rate, the time of the first attack and the first wave."""
import pytest
from test_gather import FakeServer, grid

from game import bot, run


def made(difficulty=None, attack=bot.ATTACK):
    data = grid([[64] * 8 for _ in range(8)], [])
    kw = {"difficulty": difficulty} if difficulty else {}
    return bot.Bot(FakeServer({}), data, attack=attack, chop=2.0, start={}, **kw)


def test_standard_keeps_the_bot_of_today():
    a, b = made(), made("standard")
    assert (a.attack, a.group, a.g.chop) == (b.attack, b.group, b.g.chop)


def test_easiest_attacks_later_with_fewer_soldiers_and_extreme_earlier_with_more():
    easy, std, hard = made("easiest"), made("standard"), made("extreme")
    assert easy.attack > std.attack > hard.attack and easy.group < std.group < hard.group
    assert easy.g.work_time("wood") > std.g.work_time("wood") > hard.g.work_time("wood")   # gathers slower, faster
    assert [made(n).group for n in bot.LEVELS] == sorted(made(n).group for n in bot.LEVELS)
    assert made("extreme", attack=300.0).attack == pytest.approx(300.0 * bot.LEVELS["extreme"]["attack"])   # --bot-attack


def test_a_given_group_wins():
    assert bot.Bot(FakeServer({}), grid([[64] * 8 for _ in range(8)], []), group=3, difficulty="extreme",
                   start={}).group == 3


def test_play_gives_the_setting_to_the_bot(monkeypatch, tmp_path):
    import bot as bots  # the modules of run.py (game/ on sys.path)
    import combat
    import gather as gathers
    seen = []

    class Stop(Exception):
        pass

    class FakeGather:
        bots, villagers, units, ended, speed, peers = (), [], [], None, 1.0, []

        def __init__(self, *a, **k):
            pass

        def setup(self):
            pass

    def bot_of(game, data, **kw):
        seen.append(kw.get("difficulty"))
        raise Stop
    monkeypatch.setattr(bots, "Bot", bot_of)
    monkeypatch.setattr(gathers, "Gather", FakeGather)
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    monkeypatch.setattr(run, "bot_seat", lambda players, people: (2, 1))
    (tmp_path / "aoe2mc.json").write_text('{"players": {"1": {}, "2": {}}, "tile_size": 4}')
    from test_play_speed import FakeGame
    with pytest.raises(Stop):
        run.play(FakeGame(), str(tmp_path), bot=True, ai_difficulty="hard")
    assert seen == ["hard"]


def test_the_option_lists_the_names_of_the_levels(capsys):
    with pytest.raises(SystemExit):
        run.main(["--help"])
    assert ", ".join(bot.LEVELS) in " ".join(capsys.readouterr().out.split())
    with pytest.raises(SystemExit):
        run.main(["WORLD", "--play", "--bot", "--ai-difficulty", "insane"])
