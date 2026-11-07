"""The palette tabs of the editor are computed once per process (#6056)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402

import units  # noqa: E402


def test_a_second_call_of_tabs_does_not_classify_again(monkeypatch):
    editor.tabs.cache_clear()
    first = editor.tabs()
    calls = []
    real = units.classify
    monkeypatch.setattr(units, "classify", lambda *a, **k: calls.append(a) or real(*a, **k))
    second = editor.tabs()
    assert calls == []
    assert second == first
    editor.tabs.cache_clear()
