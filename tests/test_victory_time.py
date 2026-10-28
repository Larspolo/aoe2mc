"""#2356: the AoE2 victory settings "Time Limit" (the highest score wins at the end of the time) and "Score" (the first
player at the score target wins), with the allies; a conquest still wins before."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import time_limit  # noqa: E402
from test_victory_option import loop  # noqa: E402


def side(victory, value=None, teams=None):
    """A Gather of player 1 with no server: the players 1 to 3 (teams {player: team}), its commands in g.sent."""
    g = types.SimpleNamespace(player=1, victory=victory, victory_value=value, ended=None, bots=(), peers=(), sent=[],
                              players={str(n): {"team": (teams or {}).get(n)} for n in (1, 2, 3)}, now=0.0, data={})
    g.command = lambda c: g.sent.append(c) or ""
    g.clock = lambda: g.now
    return g


def scores(monkeypatch, values):
    """score.points gives the score values {player: score} (one part)."""
    monkeypatch.setattr(time_limit.score, "points", lambda g: {n: {"military": s} for n, s in values.items()})


def titles(g):
    return [c for c in g.sent if c.startswith("title ")]


def test_the_highest_score_wins_at_the_end_of_the_time(monkeypatch):
    scores(monkeypatch, {1: 300, 2: 900, 3: 500})
    g = side("time-limit", 10, teams={2: 1, 3: 1})               # 10 years = 50 game seconds
    time_limit.tick(g, 49.0)
    assert g.ended is None and any("Time limit: 1 year left" in c for c in g.sent)
    time_limit.tick(g, 1.0)
    assert g.ended == "Defeat"                                    # player 2 and its ally 3 win
    assert "title @a[team=p1] title" in titles(g)[0] and "Defeat" in titles(g)[0]
    assert f"bossbar remove {time_limit.BAR}" in g.sent           # cheats.over closes the bar


def test_the_default_time_limit_counts_years(monkeypatch):
    scores(monkeypatch, {1: 10, 2: 5})
    g = side("time-limit")
    time_limit.tick(g, time_limit.YEARS * time_limit.YEAR - 1)
    assert g.ended is None
    time_limit.tick(g, 1)
    assert g.ended == "Victory"


def test_the_first_player_at_the_score_target_wins(monkeypatch):
    scores(monkeypatch, {1: 400, 2: 900})
    g = side("score", 1000)
    time_limit.tick(g, 0.25)
    assert g.ended is None and any("Score victory: 1000 points" in c for c in g.sent)
    scores(monkeypatch, {1: 1000, 2: 900})
    time_limit.tick(g, 0.25)
    assert g.ended is None                                        # not each tick: once each score.EVERY seconds
    g.now = time_limit.score.EVERY
    time_limit.tick(g, 0.25)
    assert g.ended == "Victory"


def test_no_end_after_a_conquest(monkeypatch):
    scores(monkeypatch, {1: 10, 2: 5})
    g = side("time-limit", 1)
    g.ended = "Defeat"                                            # conquest.tick ended the game first
    time_limit.tick(g, 100.0)
    assert g.ended == "Defeat" and g.sent == []


def test_the_game_loop_runs_the_time_limit_only_with_its_victory(monkeypatch):
    seen = []
    monkeypatch.setattr(gather.time_limit, "tick", lambda g, dt: seen.append(g.victory))
    for victory in ("time-limit", "score", "standard", "conquest"):
        calls = loop(monkeypatch, victory)
        assert ("wonder" in calls) == (victory == "standard")
    assert seen == ["time-limit"] * 4 + ["score"] * 4


def test_the_victory_value_goes_to_play(tmp_path, monkeypatch):
    import run
    (tmp_path / "level.dat").write_bytes(b"")
    seen = {}
    monkeypatch.setattr(run, "Game", lambda *a, **k: types.SimpleNamespace(start=lambda: None, stop=lambda: None,
                                                                         port=0))
    monkeypatch.setattr(run, "play", lambda *a, **k: seen.update(k) or types.SimpleNamespace(ended=None))
    monkeypatch.setattr(run, "console", lambda game: None)
    run.main([str(tmp_path), "--play", "--victory", "score", "--victory-value", "4000"])
    assert seen["victory"] == "score" and seen["victory_value"] == 4000


def test_a_saved_game_keeps_the_time_left():
    import json
    from test_loom import setup
    from game import savegame
    _, g = setup()
    g.limit_left = 123.0
    _, h = setup()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g))))
    assert h.limit_left == 123.0 and "victory_value" in savegame.SETTINGS
