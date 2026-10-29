"""#3377: a pause keeps the game time, so that a save of a paused game loads at its game time, and a recorded game
has no gap for a pause."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import pause  # noqa: E402
import recap  # noqa: E402
import run  # noqa: E402


def fake(now, t0=0.0):
    g = object.__new__(gather.Gather)
    g.tick, g.speed, g.bots, g.ended, g.t0 = 0.25, 1.0, (), None, t0
    g.clock = lambda: now[0]
    g.game = types.SimpleNamespace()
    g.commands = []
    g.command = g.commands.append
    return g


def test_a_paused_game_keeps_its_game_time_while_the_clock_runs():
    now = [10.0]
    g = fake(now)
    now[0] = 30.0
    expected = recap.game_time(g)
    pause.toggle(g, 1)
    now[0] = 50.0
    assert recap.game_time(g) == expected
    assert expected == 30.0 * gather.NORMAL


def test_a_loaded_game_goes_on_at_its_saved_game_time():
    import savegame
    now = [40.0]
    g = fake(now)
    saved = recap.game_time(g)
    h = fake([100.0])
    h.player = 1
    h.game.g, h.game.command, h.game.joined = h, lambda c: None, [1]
    savegame.load(h, {"game_time": saved, "players": {}})          # the saved game time, before the join
    run.start_on_join(h.game, [h], 1, sleep=lambda s: None)
    assert recap.game_time(h) == saved


def test_a_pause_adds_no_game_time_to_a_recording(monkeypatch):
    import record
    now = [10.0]
    g = fake(now)
    g.point, g.step, g.bots = lambda: None, lambda: None, ()
    clicks = []
    g.clicks = lambda: clicks.append(1) or ()
    g.record = types.SimpleNamespace(time=0.0, clock=g)
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    pause.toggle(g, 1)
    g.run(until=lambda: len(clicks) >= 4)                          # the clicks run, the steps and the ticks do not
    assert g.record.time == 0.0
    record.tick(g, 0.25)                                           # the record counts the game seconds of the steps
    assert g.record.time == 0.25
