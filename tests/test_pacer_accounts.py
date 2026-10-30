"""The pacer finds each Claude account in its secrets, reads the quota of each one and starts the runs on the accounts
by their missing runs (#4237, item 2 of epic #4232, docs/COLLABORATORS.md part 3)."""
import http.server
import json
import threading

import pacer
import pytest

NOW = 1_800_000_000


@pytest.fixture
def server():
    """A fake API trigger: records (path, Authorization) of each POST."""
    got = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            got.append((self.path, self.headers["Authorization"]))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *args):
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}", got
    httpd.shutdown()


def secrets(url):
    """The secrets of two accounts: the first with the present names, "BOB" with its suffix."""
    return {"CLAUDE_CODE_OAUTH_TOKEN": "t1", "PACER_URL_MAIN": f"{url}/first", "PACER_TOKEN_MAIN": "m1",
            "CLAUDE_CODE_OAUTH_TOKEN_BOB": "t2", "PACER_URL_BOB_MAIN": f"{url}/bob", "PACER_TOKEN_BOB_MAIN": "m2"}


def test_the_accounts_come_from_the_secret_names(monkeypatch):
    env = {"ALL_SECRETS": json.dumps(secrets("u"))}
    found = pacer.accounts(env, config={"accounts": {"lars": {}}})
    assert [name for name, _ in found] == ["lars", "bob"]
    assert found[1][1] == {"CLAUDE_CODE_OAUTH_TOKEN": "t2", "PACER_URL_MAIN": "u/bob", "PACER_TOKEN_MAIN": "m2"}
    assert pacer.has_url(found[0][1], "main") and not pacer.has_url(found[1][1], "deep")
    assert [name for name, _ in pacer.accounts({"PACER_URL_MAIN": "u"}, config={})] == [None]   # today's names


def test_the_runs_go_one_at_a_time_to_the_account_with_the_most_missing_runs():
    assert pacer.assign(4, {}, {"a": 3, "b": 2}, {}) == [("main", "a"), ("main", "a"), ("main", "b"), ("main", "a")]
    assert pacer.assign(2, {"deep": 1}, {"a": 3, "b": 2}, {"deep": 4.0}) == [("deep", "a"), ("main", "b")]
    assert pacer.assign(2, {}, {"a": 3, "b": 2}, {}, has=lambda a, t: a == "b") == [("main", "b")] * 2
    assert pacer.missing_runs({"a": 5, "b": 2, "c": None}, {"a": 1.5, "b": 4}) == {"a": 3.5, "b": 0.0}


def run(monkeypatch, url, reads, refs, k):
    """pacer.main with two accounts: `reads` {token: usage}, the claim refs `refs`, and a `fire` whose global limits
    give at most `k` runs. Returns (exit code, the target that the pacer gave to fire)."""
    seen = {}

    def fire(found, now, *a, target=None, skip=(), **kw):
        seen["target"] = target
        return k, {}, "x"

    monkeypatch.setattr(pacer.usage, "read_usage", lambda timeout=120, token=None: reads[token or "t1"])
    monkeypatch.setattr(pacer.usage, "read_status", lambda: ([], ""))
    monkeypatch.setattr(pacer.usage, "fire", fire)
    import health
    monkeypatch.setattr(health, "claim_refs", lambda remote="origin": refs)
    monkeypatch.setattr(health, "lane_weights", lambda comments, need=10: ({"haiku": 0.25, "deep": 4.0}, {}))
    with pytest.raises(SystemExit) as e:
        pacer.main([], env={"ALL_SECRETS": json.dumps(secrets(url))})
    return e.value.code, seen["target"]


def usage_of(used):
    return {"five_hour": (used, NOW + 3 * 3600, "allowed")}


def test_the_pacer_starts_runs_on_both_accounts_in_order_of_their_missing_runs(monkeypatch, server):
    url, got = server
    monkeypatch.setattr(pacer.datetime, "datetime", type("D", (pacer.datetime.datetime,), {
        "now": classmethod(lambda cls, tz=None: pacer.datetime.datetime.fromtimestamp(NOW, tz))}))
    reads = {"t1": usage_of(0.5), "t2": usage_of(0.1)}           # bob has more free quota
    t = str(NOW - 60)
    refs = [f"1 {t} Claim #1 by r1 (u)", f"2 {t} Claim #2 by r2 (u) account bob lane deep"]
    targets = {a: pacer.usage.target_runs(u, NOW, *pacer.usage.burns([], account=a), burn7=None)
               for a, u in (("lars", reads["t1"]), ("bob", reads["t2"]))}
    missing = {"lars": max(0, targets["lars"] - 1), "bob": max(0, targets["bob"] - 4)}
    assert missing["bob"] > missing["lars"] > 0                  # the test data: bob first, both get runs
    k = int(missing["bob"] - missing["lars"]) + 3                 # the global limits of fire: both accounts get runs ...
    assert k < missing["lars"] + missing["bob"]                   # ... but fewer than the missing runs
    code, target = run(monkeypatch, url, reads, refs, k)
    assert code == 0 and target == pytest.approx(1 + 4 + missing["lars"] + missing["bob"])
    paths = [p for p, _ in got]
    assert len(paths) == k and paths[0] == "/bob" and {"/bob", "/first"} == set(paths)
    expected = pacer.assign(k, {}, missing, {})
    assert paths == ["/bob" if a == "bob" else "/first" for _, a in expected]
    assert all(auth == ("Bearer m2" if p == "/bob" else "Bearer m1") for p, auth in got)


def test_an_account_whose_read_failed_gets_no_run(monkeypatch, server, capsys):
    url, got = server
    code, _ = run(monkeypatch, url, {"t1": usage_of(0.1), "t2": {}}, [], 3)
    assert code == 0 and [p for p, _ in got] == ["/first"] * 3
    assert "no quota read: account bob" in capsys.readouterr().out
