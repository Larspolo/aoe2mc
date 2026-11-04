"""The achievements of the state of a win or a loss: Homeless, Supremely Unexpected, Wingman, Final Countdown and
Castle of Doubt (#5644). The lines are test data in the form of data/achievements.jsonl."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import achievements  # noqa: E402
import demolish  # noqa: E402
import wonder  # noqa: E402

ROWS = [{"name": "HOMED", "event": "win homeless"},
        {"name": "ONLY", "event": "win only", "units": ["VILLAGER_MALE", "VILLAGER_FEMALE"], "civ": "SPANISH"},
        {"name": "WINGED", "event": "win ally"},
        {"name": "COUNTED", "event": "destroy WONDER", "before": 100},
        {"name": "DOUBTED", "event": "lose site CASTLE", "least": 0.95}]
GRANT = "advancement grant @a[team=p1] only aoe2mc:"


def game(monkeypatch, civ="SPANISH", teams=(None, None), share=None):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    sent = []
    players = {str(n): {"civ": civ, "team": t} for n, t in enumerate(teams, 1)}
    return SimpleNamespace(player=1, share=share, command=sent.append, data={"players": players, "objects": []},
                           players=players), sent


def test_win_homeless(monkeypatch):
    g, sent = game(monkeypatch)
    achievements.won(g, g)
    assert sent == []                                                  # a win with the start town center
    g.homeless = True
    achievements.won(g, g)
    assert sent == [GRANT + "homed"]


def test_delete_of_the_start_town_center_sets_homeless(monkeypatch):
    g, _ = game(monkeypatch)
    g.data["objects"] = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [0, 0, 16, 16]},
                         {"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [40, 40, 56, 56]}]
    g.sites = []
    monkeypatch.setattr(demolish, "shown", lambda g, rect: True)
    monkeypatch.setattr(demolish, "fall", lambda g, rect: None)
    import menu
    monkeypatch.setattr(menu, "close", lambda g, p: None)
    demolish.delete(g, None, (40, 56, 40, 56))
    assert not vars(g).get("homeless")                                  # a second town center
    demolish.delete(g, None, (0, 16, 0, 16))
    assert g.homeless


def test_win_only_villagers_as_spanish(monkeypatch):
    g, sent = game(monkeypatch)
    g.train_counts = {"VILLAGER_MALE": 3, "MILITIA": 1}
    achievements.won(g, g)
    assert sent == []                                                  # one trained militia
    g.train_counts = {"VILLAGER_MALE": 3, "VILLAGER_FEMALE": 2}
    achievements.won(g, g)
    assert sent == [GRANT + "only"]
    other, sent = game(monkeypatch, civ="FRANKS")
    other.train_counts = {"VILLAGER_MALE": 3}
    achievements.won(other, other)
    assert sent == []


def test_win_with_an_ally(monkeypatch):
    g, sent = game(monkeypatch, teams=(None, None))
    achievements.won(g, g)
    assert sent == []                                                  # no ally
    g, sent = game(monkeypatch, teams=(1, 1))
    achievements.won(g, g)
    assert sent == [GRANT + "winged"]


def test_wonder_destroyed_late_in_its_countdown(monkeypatch):
    g, sent = game(monkeypatch)
    g.bots, g.peers = [], []
    wonder.countdown(g, 2, 200)
    assert sent == []                                                  # 200 years left
    wonder.countdown(g, 1, 50)
    assert sent == []                                                  # the own wonder
    wonder.countdown(g, 2, 50)
    assert sent == [GRANT + "counted"]


def test_castle_site_lost_near_its_end(monkeypatch):
    g, sent = game(monkeypatch)
    achievements.event(g, g, "lose site CASTLE", 0.5)
    achievements.event(g, g, "lose site TOWER", 0.97)
    assert sent == []
    achievements.event(g, g, "lose site CASTLE", 0.96)
    assert sent == [GRANT + "doubted"]


def test_a_bot_gets_nothing(monkeypatch):
    g, _ = game(monkeypatch)
    bot, sent = game(monkeypatch, teams=(1, 1), share=g)
    bot.homeless = True
    achievements.won(bot, bot)
    achievements.event(bot, bot, "lose site CASTLE", 0.99)
    assert sent == []
