"""framework/tools/cycle_start.py runs in a project without tools/release.py (a bootstrap copy, #4817)."""
import sys

import cycle_start as start


def test_a_missing_release_module_gives_no_checks(monkeypatch):
    monkeypatch.setitem(sys.modules, "release", None)                  # `import release` raises ImportError
    assert start.due_checks() == []
