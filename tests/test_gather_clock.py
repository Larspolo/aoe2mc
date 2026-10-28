"""#3049: the game loop times its steps with the monotonic clock: a wall clock that goes back does not stall it."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402


def fake_clock(monkeypatch):
    """time.monotonic and time.sleep move one clock; time.time is that clock plus an offset that a test may change."""
    mono, offset = [0.0], [0.0]
    monkeypatch.setattr(gather.time, "monotonic", lambda: mono[0])
    monkeypatch.setattr(gather.time, "time", lambda: mono[0] + offset[0])
    slept = []

    def sleep(s):
        slept.append(s)
        mono[0] += s
    monkeypatch.setattr(gather.time, "sleep", sleep)
    return mono, offset, slept


def loop(monkeypatch, on_step):
    """A Gather with no server. on_step(n) runs at the start of step n (1-based)."""
    for m in (gather.conquest, gather.fog, gather.herd, gather.score):
        monkeypatch.setattr(m, "tick", lambda g: None)
    monkeypatch.setattr(gather.wonder, "tick", lambda g, dt: None)
    monkeypatch.setattr(gather.relic_victory, "tick", lambda g, dt: None)
    g = object.__new__(gather.Gather)
    g.tick, g.speed, g.bots, g.ended = 0.25, 1, (), None
    g.point = g.clicks = lambda *a: ()
    n = [0]

    def step():
        n[0] += 1
        on_step(n[0])
    g.step = step
    return g


def test_wall_clock_back_does_not_stall_the_loop(monkeypatch):
    mono, offset, slept = fake_clock(monkeypatch)

    def back(n):
        if n == 2:
            offset[0] -= 60                 # an NTP correction during the second step
    g = loop(monkeypatch, back)
    g.run(until=lambda: len(slept) >= 4)
    assert slept[:4] == [0.25] * 4          # no step sleeps for the 60 s that the wall clock lost


def test_clock_forward_during_a_step_sleeps_zero_then_normally(monkeypatch):
    mono, offset, slept = fake_clock(monkeypatch)

    def slow(n):
        if n == 2:
            mono[0] += 0.5                  # the step itself takes longer than a tick
    g = loop(monkeypatch, slow)
    g.run(until=lambda: len(slept) >= 4)
    assert slept[:4] == [0.25, 0.0, 0.25, 0.25]


def test_seconds_still_end_the_loop(monkeypatch):
    mono, offset, slept = fake_clock(monkeypatch)
    g = loop(monkeypatch, lambda n: None)
    g.run(seconds=1)
    assert len(slept) == 4                  # 4 steps of 0.25 s make the 1 s of the call
