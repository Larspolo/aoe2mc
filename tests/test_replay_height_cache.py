"""The height cache of a live replay belongs to its Replay object (#3048): an old Replay is freed after a jump back."""
import gc
import os
import sys
import weakref

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def test_replay_is_freed_after_height():
    r = replay.Replay(Fake(), data([]))
    r.height("HOUSE", 1)
    ref = weakref.ref(r)
    del r
    gc.collect()
    assert ref() is None


def test_height_is_cached_per_replay():
    r = replay.Replay(Fake(), data([]))
    calls = []
    draw = r.draw
    r.draw = lambda *a, **k: calls.append(a) or draw(*a, **k)
    first = r.height("HOUSE", 1)
    assert r.height("HOUSE", 1) == first
    assert len(calls) == 1
