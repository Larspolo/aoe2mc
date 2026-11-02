"""The "count:train" achievements (#5280): the grant comes when the trained units of the line reach its need, once."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import achievements  # noqa: E402

ROWS = [{"name": "MANY_KNIGHTS", "event": "count:train", "units": ["KNIGHT", "CAVALIER"], "need": 3},
        {"name": "CELT_SCOUTS", "event": "count:train", "units": ["SCOUT"], "need": 1, "civ": "CELTS"}]
GRANT = "advancement grant @a[team=p1] only aoe2mc:"


def game(civ="FRANKS", share=None):
    sent = []
    return SimpleNamespace(player=1, share=share, command=sent.append, data={"players": {"1": {"civ": civ}}}), sent


def test_grant_at_the_need_and_once(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game()
    for name in ("KNIGHT", "CAVALIER"):
        achievements.trained(g, name)
    assert sent == []
    achievements.trained(g, "KNIGHT")
    assert sent == [GRANT + "many_knights"]
    achievements.trained(g, "CAVALIER")
    assert sent == [GRANT + "many_knights"]


def test_other_units_and_civs_do_not_count(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game()
    for name in ("ARCHER", "ARCHER", "ARCHER", "SCOUT"):
        achievements.trained(g, name)
    assert sent == []
    g, sent = game("CELTS")
    achievements.trained(g, "SCOUT")
    assert sent == [GRANT + "celt_scouts"]


def test_no_grant_for_a_bot(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game(share=object())
    achievements.trained(g, "SCOUT")
    for _ in range(3):
        achievements.trained(g, "KNIGHT")
    assert sent == []
