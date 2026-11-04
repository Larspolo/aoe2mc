import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import mc_shot  # noqa: E402


def test_beat_runs_while_check_runs():
    calls, three = [], threading.Event()

    def fake(n):
        calls.append(n)
        if len(calls) >= 3:
            three.set()
    stop = mc_shot.beat(5783, every=0.01, call=fake)
    assert three.wait(5)                                               # the "check" still runs: beats go on
    stop.set()
    assert set(calls) == {5783}


def test_beat_survives_a_failed_call():
    calls, two = [], threading.Event()

    def fail(n):
        calls.append(n)
        if len(calls) >= 2:
            two.set()
        raise OSError("no network")
    stop = mc_shot.beat(1, every=0.01, call=fail)
    assert two.wait(5)
    stop.set()
