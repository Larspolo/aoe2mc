"""The run reports on the branch `metrics` (2026-10-29): `metrics_log.post` adds one file per report to `runs/`,
`metrics_log.load` gives them to the readers of the status comments, and `report.py --post` writes no comment."""
import datetime
import json
import subprocess

import health
import metrics_log
import pytest
import report

NOW = datetime.datetime(2026, 10, 29, 14, 30, 5, tzinfo=datetime.timezone.utc)
BODY = "Did #7. Next: #8.\n\nUsage: x · runs 3\nMetrics: ticket #7 · size:S · pr #9 · 4 min\nTokens: 0.21M eq · calls 15 · peak 62k · sinks base 58%, output 12%"


@pytest.fixture
def remote(tmp_path, monkeypatch):
    """A bare remote and two clones of it (two runs): (remote, clone a, clone b)."""
    for k in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{k}_NAME", "t")
        monkeypatch.setenv(f"GIT_{k}_EMAIL", "t@t")
    git = lambda cwd, *a: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout
    bare = tmp_path / "remote"
    git(tmp_path, "init", "-q", "--bare", str(bare))
    clones = []
    for name in ("a", "b"):
        git(tmp_path, "init", "-q", str(tmp_path / name))
        git(tmp_path / name, "remote", "add", "origin", str(bare))
        clones.append(tmp_path / name)
    return bare, *clones


def files(bare):
    out = subprocess.run(["git", "ls-tree", "-r", "--name-only", "metrics"], cwd=bare, capture_output=True, text=True)
    return out.stdout.split()


def test_a_record_has_the_keys_of_a_comment_and_a_unique_file():
    rec = metrics_log.run_record(BODY, {"session": "s-1", "lane": "haiku"}, now=NOW)
    assert rec["created_at"] == rec["updated_at"] == "2026-10-29T14:30:05Z" and rec["run"] is True
    assert rec["body"] == BODY and rec["lane"] == "haiku" and isinstance(rec["id"], int)
    other = metrics_log.run_record(BODY, {"session": "s-2"}, now=NOW)
    assert rec["id"] != other["id"] and metrics_log.run_path(rec) != metrics_log.run_path(other)
    assert metrics_log.run_path(rec).startswith("runs/2026-10-29/143005-")


def test_two_runs_add_their_records_and_the_first_one_starts_the_branch(remote):
    bare, a, b = remote
    one = metrics_log.run_record(BODY, {"session": "s-1"}, now=NOW)
    two = metrics_log.run_record(BODY.replace("#7", "#8") + " · ünïcode", {"session": "s-2"}, now=NOW)
    assert metrics_log.post(one, root=str(a)) == metrics_log.run_path(one)            # no branch yet: it starts
    subprocess.run(["git", "fetch", "-q", "origin", "+refs/heads/metrics:refs/remotes/origin/metrics"], cwd=b, check=True)
    three = metrics_log.run_record(BODY, {"session": "s-3"}, now=NOW + datetime.timedelta(seconds=1))
    assert metrics_log.post(three, root=str(a))                                         # the branch moves on
    assert metrics_log.post(two, root=str(b)) == metrics_log.run_path(two)              # b had an old tip: again
    assert sorted(files(bare)) == sorted(metrics_log.run_path(r) for r in (one, two, three))
    got = metrics_log.read_runs("origin/metrics", ["2026-10-29"], root=str(b))
    assert sorted(r["id"] for r in got) == sorted(r["id"] for r in (one, two, three))
    assert any(r["body"].endswith("ünïcode") for r in got)
    assert metrics_log.read_runs("origin/metrics", ["2026-10-28"], root=str(b)) == []


def test_post_gives_none_when_no_push_goes_through(remote):
    _, a, _ = remote
    rec = metrics_log.run_record(BODY, {}, now=NOW)
    assert metrics_log.post(rec, remote="nothing", tries=2, root=str(a)) is None


def test_the_readers_get_the_records_and_the_api_reads_from_the_newest_comment(monkeypatch):
    comment = {"id": 5, "created_at": "2026-10-29T14:00:00Z", "updated_at": "2026-10-29T14:00:00Z", "body": "owner"}
    rec = metrics_log.run_record(BODY, {"session": "s-1"}, now=NOW)
    assert metrics_log.newest([comment, rec]) == "2026-10-29T14:00:00Z"
    monkeypatch.setattr(metrics_log, "load", lambda since: [comment, rec])
    asked = []
    monkeypatch.setattr(metrics_log, "api_comments", lambda since: asked.append(since) or [])
    got = health.status_comments(since=datetime.datetime(2026, 10, 29, 13, tzinfo=datetime.timezone.utc))
    assert [c["id"] for c in got] == [5, rec["id"]] and asked == [metrics_log.parse("2026-10-29T14:00:00Z")]
    assert health.token_lines(got) and health.usage_lines(got)          # the old parsers read the body of a record


def test_report_post_writes_a_record_and_no_comment(monkeypatch, capsys):
    posted, calls = [], []
    monkeypatch.setattr(report.metrics_log, "post", lambda rec: posted.append(rec) or "runs/x.json")
    monkeypatch.setattr(report, "pages", lambda path: [{"number": 1, "body": ""}])
    monkeypatch.setattr(report, "api", lambda path, *a: calls.append((path, *a[:1])) or {"body": "", "html_url": "u"})
    monkeypatch.setattr(report, "tool", lambda *a: json.dumps({"session": "s-1", "branch": "b", "eq": 1.0})
                        if a == ("tokens.py", "--json") else "")
    monkeypatch.setattr(report, "git_lane", lambda: "haiku")
    monkeypatch.setattr(report, "measured", lambda: {"7": "read=2,code=10"})
    report.main(["--text", "Did #7.", "--usage", "Usage: x", "--ticket", "7", "--size", "S", "--result", "pr #9", "--post"])
    rec = posted[0]
    assert rec["session"] == "s-1" and rec["lane"] == "haiku" and rec["usage"] == "Usage: x" and rec["tokens"]["eq"] == 1.0
    assert rec["tickets"] == [dict(ticket=7, size="S", result="pr #9", minutes=12.0, setup=0, checks=0, checks_min=0,
                                   sinks="none", phases=dict.fromkeys(health.PHASES, 0.0) | {"read": 2.0, "code": 10.0},
                                   lane="haiku")]
    assert "Metrics: ticket #7 · size:S · pr #9 · 12 min" in rec["body"]
    assert not [c for c in calls if c[0].endswith("/comments")]                       # no comment
    assert ("issues/1", "PATCH") in calls and "runs/x.json on the branch metrics" in capsys.readouterr().out


def test_report_post_comments_when_no_push_goes_through(monkeypatch):
    calls = []
    monkeypatch.setattr(report.metrics_log, "post", lambda rec: None)
    monkeypatch.setattr(report, "pages", lambda path: [{"number": 1, "body": ""}])
    monkeypatch.setattr(report, "api", lambda path, *a: calls.append((path, *a[:1])) or {"body": "", "html_url": "u"})
    monkeypatch.setattr(report, "tool", lambda *a: "")
    monkeypatch.setattr(report, "measured", lambda: {})
    report.main(["--text", "t", "--usage", "u", "--ticket", "7", "--size", "S", "--result", "none", "--post"])
    assert ("issues/1/comments", "POST") in calls
