"""The "civ" and "mode" keys of an achievement line limit it to a civilization and a game mode (#5281)."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import achievements  # noqa: E402

ROWS = [{"name": "WIN_CELTS", "event": "win", "civ": "CELTS"},
        {"name": "WIN_REGICIDE", "event": "win", "mode": "regicide"}]


def game(civ, mode="standard", modes=()):
    sent = []
    return SimpleNamespace(player=1, share=None, command=sent.append, mode=mode, modes=set(modes),
                           data={"players": {"1": {"civ": civ}}}), sent


def test_win_with_the_named_civ_only(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game("CELTS")
    achievements.won(g, g)
    assert sent == ["advancement grant @a[team=p1] only aoe2mc:win_celts"]
    g, sent = game("FRANKS")
    achievements.won(g, g)
    assert sent == []


def test_win_in_the_named_mode_only(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    for mode, modes in (("regicide", ()), ("standard", ("regicide",))):     # --mode or a mode on top (#2490)
        g, sent = game("FRANKS", mode, modes)
        achievements.won(g, g)
        assert sent == ["advancement grant @a[team=p1] only aoe2mc:win_regicide"]
    g, sent = game("FRANKS", "death-match")
    achievements.won(g, g)
    assert sent == []
