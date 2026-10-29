"""Fewer lost claims (2026-10-29): the pacer counts the runs that it started and that have no claim yet, and
`claim.py N --or M K` tries the next candidates in the same call. In the 40 runs with a `Calls:` line, 238 of 1,161
calls were in the claim phase, and about 20 Haiku runs in 10 hours found no free ticket."""
import datetime
import json
import os
import subprocess
import sys

import dashboard
import health
import pytest

import pacer
import tokens
import usage

NOW = 1_800_000_000
TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "claim.py")


def ref(key, minutes_ago, subject):
    return f"{key} {NOW - minutes_ago * 60} {subject}"


def test_a_started_run_waits_until_it_claims():
    lines = [ref("10", 5, "Claim #10 by claude/a (x1) lane haiku"),     # a new Haiku run claimed
             ref("11", 40, "Beat #11 by claude/b"), ref("12", 3, "Claim #12 by claude/b-2 (x2)"),   # an old run
             ref("refill-0-1", 2, "Claim refill 0-1 by claude/c (x3)"),  # a new deep run refills
             ref("13", 30, "Claim #13 by claude/d (x4)")]                 # older than the window
    started = {"haiku": 3, "main": 2, "deep": 1}
    assert usage.pending(started, lines, NOW) == {"haiku": 2, "main": 2}
    assert usage.pending(started, lines, NOW, refill_lane=None) == {"haiku": 2, "main": 1, "deep": 1}
    assert usage.pending({}, lines, NOW) == {} and usage.pending({"main": 1}, None, NOW) == {"main": 1}


TICKETS = [{"number": 20 + i, "labels": [{"name": "lane:haiku"}, {"name": "P2"}], "body": "", "title": f"T{i}",
            "created_at": "2027-01-15T08:00:00Z"} for i in range(3)]


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(dashboard, "pages", lambda path: TICKETS)
    monkeypatch.setattr(dashboard, "api", lambda path: {"total_count": 0})
    monkeypatch.setattr(usage, "read_flow", lambda now: (None, "flow ok"))
    monkeypatch.setattr(usage, "due_reviews", lambda **_: [])
    monkeypatch.setattr(usage, "release_due", lambda: [])
    monkeypatch.setattr(usage, "free_sources", lambda: [])
    monkeypatch.setattr(usage, "target_runs", lambda *a, **kw: 40)
    refs = []
    monkeypatch.setattr(health, "claim_refs", lambda remote="origin": refs)
    return refs


def fire(**kw):
    return usage.fire({"five_hour": (0.2, NOW + 3 * 3600, "allowed")}, NOW, status=([], ""), **kw)


def test_the_pending_lane_runs_take_their_tickets_first(fake):
    k, runs, line = fire()
    assert runs["haiku"] == 3 and "pending" not in line
    k, runs, line = fire(started={"haiku": 2})
    assert runs["haiku"] == 1 and 'pending {"haiku": 2}' in line
    fake.append(ref("20", 4, "Claim #20 by claude/h1 (x) lane haiku"))  # one of them claimed: one ticket less
    k, runs, line = fire(started={"haiku": 2})
    assert 'pending {"haiku": 1}' in line


def test_the_pacer_reads_the_starts_of_the_last_minutes_from_its_log(tmp_path):
    at = lambda minutes_ago: f"{datetime.datetime.fromtimestamp(NOW - minutes_ago * 60, datetime.timezone.utc):%Y-%m-%dT%H:%M:%SZ}"
    log = tmp_path / "pacer.jsonl"
    log.write_text("\n".join([json.dumps({"at": at(20), "started": {"main": 4}}),
                              json.dumps({"at": at(10), "started": {"haiku": 2, "main": 1}}),
                              json.dumps({"at": at(1), "started": {"main": 1}}), "{cut"]) + "\n")
    assert pacer.recent_starts(log, NOW) == {"haiku": 2, "main": 2}
    assert pacer.recent_starts(tmp_path / "none.jsonl", NOW) == {}


@pytest.fixture
def clones(tmp_path):
    run = lambda *a, cwd: subprocess.run(a, cwd=cwd, capture_output=True, text=True, check=True)
    remote = tmp_path / "remote.git"
    run("git", "init", "-q", "--bare", str(remote), cwd=tmp_path)
    out = []
    for i in range(3):
        d = tmp_path / f"run{i}"
        run("git", "init", "-q", "-b", f"run-{i}", str(d), cwd=tmp_path)
        run("git", "remote", "add", "origin", str(remote), cwd=d)
        for k, v in (("user.name", "t"), ("user.email", "t@t")):
            run("git", "config", k, v, cwd=d)
        out.append(d)
    return out


def claim(d, *args):
    return subprocess.run([sys.executable, TOOL, *args], cwd=d, capture_output=True, text=True)


def test_or_claims_the_first_free_candidate_in_one_call(clones):
    assert claim(clones[0], "7").returncode == 0
    r = claim(clones[1], "7", "--or", "8", "9")
    assert r.returncode == 0 and "#7 owned by another run" in r.stdout and "claimed claim/8" in r.stdout
    r = claim(clones[2], "7", "--or", "8")
    assert r.returncode == 1 and "#8 owned by another run" in r.stdout


def test_the_phases_see_the_ticket_that_or_won():
    assert tokens.claim_numbers("python3 tools/claim.py 7 --or 8 9; echo rc=$?") == [7, 8, 9]
    assert tokens.claim_numbers("python3 tools/claim.py 7 --guard") == []
    block = {"type": "tool_result", "content": "#7 owned by another run: x\nclaimed claim/8\n"}
    assert tokens.won(block, [7, 8, 9]) == 8 and tokens.won(block, [7]) is None
