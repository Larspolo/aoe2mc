"""The achievements of a research, a building, Auto Scout, a unit of a building and a win against a bot (#5629)."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import achievements  # noqa: E402
import cheats  # noqa: E402

ROWS = [{"name": "LOOMED", "event": "research LOOM"},
        {"name": "WONDERED", "event": "build WONDER"},
        {"name": "SCOUTED", "event": "autoscout"},
        {"name": "DONJONED", "event": "train SERJEANT at DONJON"},
        {"name": "BEAT_HARD", "event": "win ai hard"}]
GRANT = "advancement grant @a[team=p1] only aoe2mc:"


def game(share=None):
    sent = []
    return SimpleNamespace(player=1, share=share, command=sent.append, data={"players": {"1": {"civ": "FRANKS"}}}), sent


def test_each_event_grants_its_line_once(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game()
    for name in ("research LOOM", "build WONDER", "autoscout", "research LOOM"):
        achievements.event(g, g, name)
    achievements.trained(g, "SERJEANT", "DONJON")
    achievements.won(g, g, {"hard"})
    assert sent == [GRANT + k for k in ("loomed", "wondered", "scouted", "donjoned", "beat_hard")]


def test_other_events_and_bots_grant_nothing(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game()
    for name in ("research WHEELBARROW", "build CASTLE"):
        achievements.event(g, g, name)
    achievements.trained(g, "SERJEANT", "CASTLE")
    achievements.trained(g, "SERJEANT")
    achievements.won(g, g, {"easiest", "moderate"})
    assert sent == []
    bot, sent = game(share=g)
    achievements.event(bot, bot, "research LOOM")
    assert sent == []


def test_over_gives_the_levels_of_the_bots_that_lost(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    got = []
    monkeypatch.setattr(achievements, "won", lambda g, h, levels=(): got.append((h.player, levels)))
    import fog
    import recap
    monkeypatch.setattr(recap, "give", lambda g, won: None)
    h = SimpleNamespace(player=1, share=None)
    bots = [SimpleNamespace(difficulty="hard", g=SimpleNamespace(player=2, share=h)),
            SimpleNamespace(difficulty="easiest", g=SimpleNamespace(player=3, share=h))]
    g = SimpleNamespace(player=1, bots=bots, command=lambda c: None, data={})
    monkeypatch.setattr(fog, "gathers", lambda g: [h])
    monkeypatch.setattr(cheats, "title", lambda *a: None)
    monkeypatch.setattr(cheats, "tune", lambda *a: None)
    import music
    monkeypatch.setattr(music, "stop", lambda g: None)
    for mod in ("wonder", "relic_victory", "hill", "time_limit", "treaty"):
        monkeypatch.setattr(__import__(mod), "close", lambda h: None)
    import scenario
    monkeypatch.setattr(scenario, "ending", lambda *a: [])
    cheats.over(g, lambda n: n in (1, 3))
    assert got == [(1, {"hard"})]
