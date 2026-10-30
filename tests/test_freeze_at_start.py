"""The ticks freeze when the server is up, not when play() starts (#3974): a client that starts before play() let
the trigger timers of the first seconds run before the join."""
import contextlib
import io
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import run  # noqa: E402
from test_start_on_join import FakeGame, Side  # noqa: E402


def test_main_makes_a_game_that_freezes_at_the_start(monkeypatch, tmp_path):
    (tmp_path / "level.dat").write_bytes(b"")
    made = []

    class Game(FakeGame):
        def start(self):
            made.append(self.wait)

    def make(*a, **k):
        return Game()
    monkeypatch.setattr(run, "Game", make)
    monkeypatch.setattr(run, "play", lambda *a, **k: type("G", (), {"ended": None})())
    monkeypatch.setattr(run, "console", lambda game: None)
    monkeypatch.setattr(run, "ctrl_c", lambda: None)
    run.main([str(tmp_path), "--play"])
    assert made == [True]


def test_freeze_stops_the_timers_and_the_tick_triggers():
    game = FakeGame()
    run.freeze(game)
    assert game.sent == ["tick freeze", "scoreboard players set #wait aoe_trig 1"]


def test_the_start_ends_the_wait_of_a_restart():
    game = FakeGame()
    game.joined, game.wait = {"Steve"}, True
    run.start_on_join(game, [Side(lambda: 0.0)], 1, sleep=lambda s: None)
    assert game.wait is False


def fired(game):
    return "has 1" in game.command("scoreboard players get #probe aoe_trig")


@pytest.mark.mc
def test_a_timer_trigger_fires_after_the_join_not_before(tmp_path):
    import scenarios
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    from test_triggers_server import wait

    import aoe2mc
    if not mojang_reachable() or not paper_reachable():
        pytest.skip("Mojang or Paper is not available")
    src, world = scenarios.triggers(str(tmp_path / "t.aoe2scenario")), str(tmp_path / "W")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, world)
    with open(os.path.join(world, "datapacks", "aoe2mc", "data", "aoe2mc", "function", "trigger", "0.mcfunction"),
              "a") as f:                                               # a timer trigger sets no score: a probe
        f.write("scoreboard players set #probe aoe_trig 1\n")
    with run.Game(world, wait=True) as game:
        time.sleep(10)                                                 # a client starts (25 s in the check of #3783)
        assert not fired(game)                                      # "Welcome" at 5 s with its SEND_CHAT
        game.joined = {"aoe2mc"}                                       # a fake join
        run.start_on_join(game, [], 1)
        t0 = time.time()
        assert wait(lambda: fired(game), 20)
        assert time.time() - t0 > 3                                    # 5 s after the join, not at once
