"""The game and the scenario trigger timers start when the people joined (#3314)."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import run  # noqa: E402


class FakeGame:
    joined = frozenset()

    def __init__(self, *a, **k):
        self.sent, self.people, self.settings, self.port = [], 1, {}, 0

    def command(self, cmd):
        self.sent.append(cmd)

    def start(self):
        pass

    def stop(self):
        pass


class Side:
    def __init__(self, clock):
        self.clock, self.t0 = clock, clock()


def join_after(game, names, now):
    """A sleep that lets one more person join on each call, and moves the clock."""
    def sleep(s):
        now[0] += 10
        game.joined = {*game.joined, names[len(game.joined)]}
    return sleep


@pytest.mark.parametrize("people", [1, 2])
def test_unfreeze_and_clock_start_after_the_last_join(people):
    game, now = FakeGame(), [0.0]
    sides = [Side(lambda: now[0]) for _ in range(people + 1)]       # the people and a bot
    sleep = join_after(game, ["Steve", "Alex"], now)
    run.start_on_join(game, sides, people, sleep=lambda s: (game.command("sleep"), sleep(s)))
    assert game.sent == ["sleep"] * people + ["scoreboard players reset #wait aoe_trig", "tick unfreeze"]
    assert len(game.joined) == people
    assert all(h.t0 == now[0] == 10 * people for h in sides)    # the game clock is 0 at the last join


def test_main_lets_play_wait(monkeypatch, tmp_path):
    (tmp_path / "level.dat").write_bytes(b"")
    seen = {}
    games = []

    def make(*a, **k):
        games.append(FakeGame())
        return games[-1]

    def play(game, world, log, *a, **kw):
        seen["sent"], seen["wait"] = list(game.sent), kw.get("wait")
        return type("G", (), {"ended": None})()
    monkeypatch.setattr(run, "Game", make)
    monkeypatch.setattr(run, "play", play)
    monkeypatch.setattr(run, "console", lambda game: None)
    monkeypatch.setattr(run, "ctrl_c", lambda: None)
    run.main([str(tmp_path), "--play"])
    assert seen == {"sent": [], "wait": True}



def test_play_freezes_the_ticks_first(monkeypatch, tmp_path):
    import gather as gathers
    from test_play_speed import FakeGame as PlayGame

    class Stop(Exception):
        pass

    def gather(*a, **k):
        raise Stop
    monkeypatch.setattr(gathers, "Gather", gather)
    (tmp_path / "aoe2mc.json").write_text('{"players": {"1": {}, "2": {}}, "tile_size": 4}')
    game = PlayGame()
    with pytest.raises(Stop):
        run.play(game, str(tmp_path), wait=True)
    assert game.commands[:1] == ["tick freeze"]
    game = PlayGame()
    with pytest.raises(Stop):
        run.play(game, str(tmp_path))                                  # the tests: no freeze, no wait
    assert "tick freeze" not in game.commands

@pytest.mark.mc
def test_a_late_client_gets_the_first_timed_message(tmp_path):
    import contextlib
    import io
    import shutil
    import threading
    import time

    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    from test_triggers_server import WELCOME, wait

    import aoe2mc
    from tools import scenarios
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    src, world = scenarios.triggers(str(tmp_path / "t.aoe2scenario")), str(tmp_path / "W")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, world)
    with run.Game(world) as game:
        threading.Thread(target=run.play, args=(game, world), kwargs={"mode": "scenario", "wait": True, "seconds": 90},
                         daemon=True).start()
        time.sleep(20)                                                  # the person comes late (#3224: 22.8 s)
        with mc_shot.Client(game.game_port, game.version) as client:
            client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
            assert wait(lambda: WELCOME in client.text(), 30), client.text()[-2000:]
