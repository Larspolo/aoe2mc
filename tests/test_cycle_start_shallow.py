"""framework/tools/cycle_start.py names a closed "Fix main" ticket also in a shallow clone, many hours after the fix (#3305)."""
import subprocess

import cycle_start as start
import dashboard

RED = [("last", "success", "049070c", "2026-10-28T20:58"), ("night", "failure", "9c9d017", "2026-10-28T09:36")]
FIX = {"number": 3212, "title": "Fix main: elevation damage test fails on the night CI run", "labels": [{"name": "P0"}],
       "closed_at": "2026-10-28T19:35:05Z"}


def fake(monkeypatch, closed_p0):
    """A GitHub with 100 other closed issues on the first page, `closed_p0` as the closed P0 issues, and an empty git
    log (a shallow clone that starts after the fix)."""
    other = [{"number": 4000 + k, "title": f"Ticket {k}", "labels": [], "closed_at": "2026-10-28T20:50:00Z"}
             for k in range(100)]
    monkeypatch.setattr(dashboard, "api", lambda path: other)
    monkeypatch.setattr(dashboard, "pages", lambda path, limit=10: closed_p0 if "labels=P0" in path else other)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="", stderr=""))


def test_a_fix_main_ticket_out_of_the_last_100_closed_issues_is_named(monkeypatch):
    fake(monkeypatch, [FIX])
    line = start.ci_line(RED, {})
    assert "→ red: open P0 tickets \"Fix main\": none" in line
    assert line.endswith("; closed after the red run: #3212 Fix main: elevation damage test fails on the night CI run")


def test_no_closed_fix_gives_only_the_red_line(monkeypatch):
    fake(monkeypatch, [])
    assert start.ci_line(RED, {}).endswith("→ red: open P0 tickets \"Fix main\": none")


def test_a_green_main_gives_only_the_runs(monkeypatch):
    fake(monkeypatch, [FIX])
    green = [(n, "success", sha, t) for n, _, sha, t in RED]
    assert start.ci_line(green, {}) == "last success (049070c, 2026-10-28T20:58) · night success (9c9d017, 2026-10-28T09:36)"
