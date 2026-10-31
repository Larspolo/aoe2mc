"""The game program grants the achievements of a win and of an age (#5279)."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import achievements  # noqa: E402

ROWS = [{"name": "WIN_ANY", "event": "win"}, {"name": "WIN_CELTS", "event": "win CELTS"},
        {"name": "FAST_CASTLE", "event": "age CASTLE_AGE", "before": 600}]


def game(n, share=None):
    sent = []
    return SimpleNamespace(player=n, share=share, command=sent.append, data={"players": {str(n): {"civ": "CELTS"}}}), sent


def test_win_grants_to_the_team_of_the_winner_once(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game(2)
    achievements.won(g, g)
    achievements.won(g, g)
    assert sent == ["advancement grant @a[team=p2] only aoe2mc:win_any",
                    "advancement grant @a[team=p2] only aoe2mc:win_celts"]


def test_age_before_its_time_only(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game(1)
    achievements.aged(g, "CASTLE_AGE", 700)
    assert sent == []
    achievements.aged(g, "CASTLE_AGE", 500)
    achievements.aged(g, "CASTLE_AGE", 500)
    assert sent == ["advancement grant @a[team=p1] only aoe2mc:fast_castle"]


def test_bot_gets_none(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game(3, share=object())
    achievements.won(g, g)
    achievements.aged(g, "CASTLE_AGE", 1)
    assert sent == []


def test_unknown_key_is_not_granted(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game(1)
    achievements.grant(g, 1, "nothing")
    assert sent == []
