"""The briefs of the pacer (owner, 2026-10-29): the pacer claims a ticket for each run that it starts, sends the ticket
in the `text` of the call, and the run adopts the claim (`claim.py N --adopt NAME`)."""
import http.server
import json
import os
import subprocess
import sys
import threading

import pytest

import claim
import pacer

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "claim.py")


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


@pytest.fixture
def clones(tmp_path):
    """A bare remote and two clones on the branches run-0 (the pacer) and run-1 (the run)."""
    remote = tmp_path / "remote.git"
    git("init", "-q", "--bare", str(remote), cwd=tmp_path)
    out = []
    for i in range(2):
        d = tmp_path / f"run{i}"
        git("init", "-q", "-b", f"run-{i}", str(d), cwd=tmp_path)
        git("remote", "add", "origin", str(remote), cwd=d)
        for k, v in (("user.name", "t"), ("user.email", "t@t")):
            git("config", k, v, cwd=d)
        out.append(d)
    return out


def tool(d, *args):
    return subprocess.run([sys.executable, TOOL, *args], cwd=d, capture_output=True, text=True)


@pytest.fixture
def server():
    """A fake API trigger: records the JSON body of each POST; the path "/down" answers 500."""
    got = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            got.append((self.path, json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))))
            self.send_response(500 if self.path == "/down" else 200)
            self.end_headers()
            self.wfile.write(b'{"type": "routine_fire", "claude_code_session_url": "https://example.invalid/s"}')

        def log_message(self, *args):
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}", got
    httpd.shutdown()


def test_the_run_adopts_the_claim_of_the_pacer_and_its_lane(clones, monkeypatch):
    monkeypatch.chdir(clones[0])
    assert claim.claim(7, by="pacer-rabc", tag=" lane haiku")
    r = tool(clones[1], "7", "--adopt", "pacer-rabc")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git("config", "--get", "aoe2mc.lane", cwd=clones[1]).strip() == "haiku"
    assert tool(clones[1], "7", "--beat").returncode == 0           # the claim is the run's now
    assert claim.subject("claim/7").startswith("Beat #7 by run-1") and claim.subject("claim/7").endswith(" lane haiku")
    assert tool(clones[0], "7", "--adopt", "pacer-rabc").returncode == 1   # a second adopt finds the run's claim


def test_a_released_claim_is_not_adopted(clones, monkeypatch):
    monkeypatch.chdir(clones[0])
    assert claim.claim(8, by="pacer-rdef", tag="")
    assert claim.release(8, by="pacer-rdef")
    assert tool(clones[1], "8", "--adopt", "pacer-rdef").returncode == 1


def briefs(monkeypatch, tickets, out=None):
    monkeypatch.setattr(pacer, "red_main", lambda: False)
    monkeypatch.setattr(pacer, "queues", lambda open_all, refs, now, tasks: {t: list(tickets) for t in tasks})
    monkeypatch.setattr(pacer, "brief", lambda issue, comments, name, task, sample: f"{pacer.HEAD}\nticket: {issue['number']}\nclaim: {name}")
    monkeypatch.setattr(claim, "start", lambda n, by=None, note="": None)
    import dashboard
    monkeypatch.setattr(dashboard, "pages", lambda path, limit=10: [])
    found = {"five_hour": (0.2, 0, "allowed")}
    return pacer.Briefs([("main", "u", "t")], {"open": [], **(out or {})}, 0, found)


def test_each_run_gets_its_own_claimed_ticket_in_the_text(clones, monkeypatch, server):
    url, got = server
    monkeypatch.chdir(clones[0])
    b = briefs(monkeypatch, [{"number": 5}, {"number": 6}])
    b.start("main", f"{url}/main", "t")
    b.start("main", f"{url}/main", "t")
    b.start("main", f"{url}/main", "t")                             # no ticket left: a run with no brief
    texts = [body.get("text") for _, body in got]
    assert [t.split("\n")[1] if t else None for t in texts] == ["ticket: 5", "ticket: 6", None]
    assert b.given == [5, 6]
    name = texts[0].split("\n")[2].split(": ")[1]
    assert claim.subject("claim/5").startswith(f"Claim #5 by {name} ")


def test_a_failed_call_releases_the_claim(clones, monkeypatch, server):
    url, got = server
    monkeypatch.chdir(clones[0])
    b = briefs(monkeypatch, [{"number": 9}])
    with pytest.raises(Exception):
        b.start("main", f"{url}/down", "t")
    assert claim.subject("claim/9").startswith("Release #9") and b.given == []


def test_no_brief_while_the_flow_brake_is_on(monkeypatch):
    assert briefs(monkeypatch, [{"number": 5}], {"flow": 1}).todo is None


def test_a_long_brief_is_cut(monkeypatch):
    import ticket_context
    monkeypatch.setattr(ticket_context, "context", lambda body: "x" * 1000)
    text = pacer.brief({"number": 3, "title": "T", "body": "b"}, [], "pacer-r1", "main", "Usage: u", limit=300)
    assert len(text) <= 300 and text.startswith(f"{pacer.HEAD}\nticket: 3\nclaim: pacer-r1\nlane: main\nusage: Usage: u")
