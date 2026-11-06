"""framework/tools/ship_pr.py runs the scan tests of `[ci] scans` for a change under `[ci] scan_paths`, also with
`--tested` (#5908): no import connects them to a changed module."""
import types

import ship_pr as ship


def fake(monkeypatch, code=0):
    calls = []
    monkeypatch.setattr(ship, "SCANS", ("tests/test_scan.py",))
    monkeypatch.setattr(ship, "SCAN_PATHS", ("game/",))
    monkeypatch.setattr(ship.os.path, "isfile", lambda f: True)
    monkeypatch.setattr(ship.subprocess, "run", lambda cmd, **k: (calls.append(cmd), types.SimpleNamespace(
        returncode=code, stdout="1 failed" if code else "1 passed", stderr=""))[1])
    return calls


def test_a_game_change_runs_the_scan(monkeypatch):
    calls = fake(monkeypatch)
    assert ship.scans(["game/gather.py", "docs/a.md"])
    assert calls and calls[0][-1] == "tests/test_scan.py"


def test_a_docs_change_runs_no_scan(monkeypatch):
    calls = fake(monkeypatch)
    assert ship.scans(["docs/a.md"]) and not calls


def test_a_failed_scan_stops_the_push(monkeypatch):
    fake(monkeypatch, code=1)
    assert not ship.scans(["game/gather.py"])

