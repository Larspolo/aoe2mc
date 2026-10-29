"""#2490: the AoE2 DE advanced settings "Regicide Mode", "Sudden Death Mode" and "Empire Wars Mode" go on top of another
game mode (AoE2 wiki "Random map", "Advanced Settings"): `run.py --play --mode capture-the-relic --regicide`."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import build  # noqa: E402
import capture_relic  # noqa: E402
import combat  # noqa: E402
import empire_wars  # noqa: E402
import gather  # noqa: E402
import regicide  # noqa: E402
import run  # noqa: E402
import sudden_death  # noqa: E402
import train  # noqa: E402
from test_sudden_death import game as town_game  # noqa: E402


def play(tmp_path, monkeypatch, state=None, **settings):
    """run.play on a fake Gather: the setups and the age start that it calls, the mode and modes of the Gather."""
    (tmp_path / "aoe2mc.json").write_text('{"players": [], "tile_size": 4}')
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed = (), [], [], None, 1.0

        def __init__(self, *a, **k):
            pass

        def setup(self):
            pass

        def run(self, seconds):
            seen.append((self.mode, sorted(self.modes)))
    monkeypatch.setattr(gather, "Gather", FakeGather)
    for m in (capture_relic, regicide, sudden_death):
        monkeypatch.setattr(m, "setup", lambda g, mode, **start: seen.append(f"setup {mode}"))   # regicide (#2388)
    monkeypatch.setattr(empire_wars, "setup", lambda g, mode: seen.append(f"setup {mode}"))
    monkeypatch.setattr(train, "start", lambda g, age: seen.append(f"age {age}"))
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    import savegame
    monkeypatch.setattr(savegame, "load", lambda g, d: None)
    from test_play_speed import FakeGame
    run.play(FakeGame(), str(tmp_path), state=state, **settings)
    return seen


def test_regicide_on_top_of_capture_the_relic_sets_up_both(tmp_path, monkeypatch):
    seen = play(tmp_path, monkeypatch, mode="capture-the-relic", regicide=True)
    assert seen == ["setup capture-the-relic", "setup regicide",
                    ("capture-the-relic", ["capture-the-relic", "regicide"])]


def test_sudden_death_and_empire_wars_on_top_of_regicide(tmp_path, monkeypatch):
    seen = play(tmp_path, monkeypatch, mode="regicide", sudden_death=True, empire_wars=True)
    assert seen == [f"age {run.MODES['empire-wars']['age']}", "setup empire-wars", "setup regicide", "setup sudden-death",
                    ("regicide", ["empire-wars", "regicide", "sudden-death"])]


def test_a_mode_alone_works_as_before(tmp_path, monkeypatch):
    assert play(tmp_path, monkeypatch, mode="regicide") == ["setup regicide", ("regicide", ["regicide"])]
    assert play(tmp_path, monkeypatch, mode="empire-wars") == [f"age {run.MODES['empire-wars']['age']}", "setup empire-wars",
                                                               ("empire-wars", ["empire-wars"])]
    assert play(tmp_path, monkeypatch) == [("standard", [])]


def test_a_loaded_game_gets_no_second_town_or_relic(tmp_path, monkeypatch):
    seen = play(tmp_path, monkeypatch, state={"players": {}}, mode="capture-the-relic", empire_wars=True,
                regicide=True)
    assert seen == ["setup regicide", ("capture-the-relic", ["capture-the-relic", "empire-wars", "regicide"])]


def test_the_run_loop_checks_the_king_and_the_relic_together(monkeypatch):
    calls = []
    for m in (gather.conquest, gather.fog, gather.herd, gather.regicide, gather.sudden_death, gather.capture_relic):
        monkeypatch.setattr(m, "tick", lambda g, m=m: calls.append(m.__name__))
    monkeypatch.setattr(gather.wonder, "tick", lambda g, dt: None)
    monkeypatch.setattr(gather.relic_victory, "tick", lambda g, dt: None)
    monkeypatch.setattr(gather.score, "tick", lambda g: None)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    g = object.__new__(gather.Gather)
    g.tick, g.bots, g.ended, g.mode = 0.25, (), None, "capture-the-relic"
    g.modes = frozenset({"capture-the-relic", "regicide", "sudden-death"})
    g.point = g.step = lambda: None
    g.clicks = lambda: ()
    g.run(until=lambda: calls.count("conquest") >= 2)
    assert calls.count("regicide") == calls.count("sudden_death") == calls.count("capture_relic") == 2


def test_the_king_and_the_relic_both_decide_the_game(monkeypatch):
    """The loss of the King defeats a player (regicide.tick), and the center relic still wins (capture_relic.tick)."""
    server, g = town_game()
    g.mode, g.modes = "capture-the-relic", frozenset({"capture-the-relic", "regicide"})
    over = []
    monkeypatch.setattr(regicide.conquest.cheats, "over", lambda g, won: over.append("regicide"))
    monkeypatch.setattr(regicide, "has_king", lambda g, n: n != 2)          # the King of player 2 died
    g.kings, g.regicide_at = {1, 2}, 0.0
    regicide.tick(g)
    assert 2 in g.defeated
    monkeypatch.setattr(capture_relic.cheats, "over", lambda g, won: over.append("relic") or "relic")
    monkeypatch.setattr(capture_relic.monk, "relics", lambda h: [{"center": True, "home": (2, 6, 2, 6)}])
    monkeypatch.setattr(capture_relic.monk, "monasteries", lambda h: {(2, 6, 2, 6)})
    capture_relic.tick(g)
    assert over[-1] == "relic"


def test_sudden_death_on_top_of_another_mode_refuses_a_second_town_center():
    server, g = town_game()
    g.mode, g.modes = "capture-the-relic", frozenset({"capture-the-relic", "sudden-death"})
    assert build.locked(g, "TOWN_CENTER") == "Sudden Death: only one town center"
    g.modes = frozenset({"capture-the-relic"})
    assert build.locked(g, "TOWN_CENTER") != "Sudden Death: only one town center"


def test_the_options_go_to_play(tmp_path, monkeypatch):
    (tmp_path / "level.dat").write_bytes(b"")
    seen = {}
    monkeypatch.setattr(run, "Game", lambda *a, **k: types.SimpleNamespace(start=lambda: None, stop=lambda: None,
                                                                         port=0))
    monkeypatch.setattr(run, "play", lambda *a, **k: seen.update(k) or types.SimpleNamespace(ended=None))
    monkeypatch.setattr(run, "console", lambda game: None)
    run.main([str(tmp_path), "--play", "--mode", "capture-the-relic", "--regicide", "--sudden-death"])
    assert (seen["mode"], seen["regicide"], seen["sudden_death"], seen["empire_wars"]) == \
        ("capture-the-relic", True, True, False)
