"""The "count:gather" achievements (#5643): the grant comes when the gathered amount of the line reaches its need, once,
only with its civilization and age, not to a bot."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import achievements  # noqa: E402
import build  # noqa: E402
import savegame  # noqa: E402

ROWS = [{"name": "DARK_EAT", "event": "count:gather", "gather": "WILD_BOAR", "need": 2, "age": 0},
        {"name": "MANY_SHEEP", "event": "count:gather", "gather": "SHEEP", "need": 3},
        {"name": "POLE_FOOD", "event": "count:gather", "gather": "FOLWARK", "need": 50, "civ": "POLES"}]
GRANT = "advancement grant @a[team=p1] only aoe2mc:"


def game(civ="FRANKS", share=None):
    sent = []
    return SimpleNamespace(player=1, share=share, command=sent.append, techs=set(),
                           data={"players": {"1": {"civ": civ}}}), sent


def test_grant_at_the_need_and_once(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game()
    for _ in range(2):
        achievements.gathered(g, "SHEEP")
    assert sent == []
    achievements.gathered(g, "SHEEP")
    achievements.gathered(g, "SHEEP")
    assert sent == [GRANT + "many_sheep"]


def test_amounts_and_civ(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game()
    achievements.gathered(g, "FOLWARK", 60)
    assert sent == []
    g, sent = game("POLES")
    achievements.gathered(g, "FOLWARK", 30)
    assert sent == []
    achievements.gathered(g, "FOLWARK", 20.0)
    assert sent == [GRANT + "pole_food"]


def test_no_dark_age_grant_after_the_feudal_age(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game()
    achievements.gathered(g, "WILD_BOAR")
    g.techs.add(build.AGE_TECHS[0])
    achievements.gathered(g, "WILD_BOAR")
    assert sent == []
    g, sent = game()
    achievements.gathered(g, "WILD_BOAR")
    achievements.gathered(g, "WILD_BOAR")
    assert sent == [GRANT + "dark_eat"]


def test_no_grant_for_a_bot(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game(share=object())
    for _ in range(5):
        achievements.gathered(g, "SHEEP")
    assert sent == []


def test_the_save_keeps_the_counts():
    assert "gather_counts" in savegame.OPTIONAL
