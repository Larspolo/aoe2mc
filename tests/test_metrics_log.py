"""The log of the status comments on the branch `metrics` (#1983): `framework/tools/metrics_log.py` and its use in health.py."""
import datetime
import json
import subprocess

import health
import metrics_log

NOW = datetime.datetime(2026, 10, 27, 20, tzinfo=datetime.timezone.utc)


def comment(i, created, updated=None, body="Usage: Usage: x"):     # a malformed line is stored as it is
    return {"id": i, "created_at": created, "updated_at": updated or created, "issue_url": "x/issues/1", "body": body,
            "user": {"login": "x"}}


def fake(comments, calls):
    def api(path):
        calls.append(path)
        if path.startswith("issues?state=open"):
            return [{"number": 1}]
        since = path.split("since=")[1].split("&")[0]
        return [c for c in comments if c["updated_at"] >= since]
    return api


def lines(root):
    return [json.loads(x) for p in sorted((root / "status").glob("*.jsonl")) for x in p.read_text().splitlines()]


def test_add_twice_gives_the_same_files_and_an_edit_replaces_its_line(tmp_path, monkeypatch):
    src = [comment(1, "2026-10-26T23:59:00Z"), comment(2, "2026-10-27T10:00:00Z", body="Metrics: ticket #5")]
    calls = []
    monkeypatch.setattr(metrics_log, "api", fake(src, calls))
    assert metrics_log.update(tmp_path, now=NOW) == [str(tmp_path / "status" / f"2026-10-2{d}.jsonl") for d in (6, 7)]
    assert "since=2026-10-20T20:00:00Z" in calls[1]                        # an empty log: 7 days
    first = lines(tmp_path)
    assert [c["id"] for c in first] == [1, 2] and set(first[0]) == set(metrics_log.KEYS)
    assert metrics_log.update(tmp_path, now=NOW) == [] and lines(tmp_path) == first
    assert "since=2026-10-27T10:00:00Z" in calls[-1]                       # from the newest stored comment
    src[0] = comment(1, "2026-10-26T23:59:00Z", "2026-10-27T11:00:00Z", "edited")
    assert metrics_log.update(tmp_path, now=NOW) == [str(tmp_path / "status" / "2026-10-26.jsonl")]
    assert [c["body"] for c in lines(tmp_path)] == ["edited", "Metrics: ticket #5"]


def test_days_reads_the_period_again(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(metrics_log, "api", fake([comment(1, "2026-10-27T10:00:00Z")], calls))
    metrics_log.update(tmp_path, now=NOW)
    metrics_log.update(tmp_path, days=2, now=NOW)
    assert "since=2026-10-25T20:00:00Z" in calls[-1]


def test_status_comments_are_the_same_with_the_log_and_without(tmp_path, monkeypatch):
    src = [comment(i, f"2026-10-27T1{i}:00:00Z") for i in range(5)]
    monkeypatch.setattr(metrics_log, "api", fake(src, []))
    since = datetime.datetime(2026, 10, 27, 11, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(metrics_log, "load", lambda since: None)
    api_only = health.status_comments(since=since)
    metrics_log.add(tmp_path, src[:3])                                      # the log is 2 comments behind
    stored = [c for c in metrics_log.read_dir(tmp_path).values() if c["created_at"] >= "2026-10-27T11:00:00Z"]
    monkeypatch.setattr(metrics_log, "load", lambda since: stored)
    assert [c["id"] for c in health.status_comments(since=since)] == [c["id"] for c in api_only] == [1, 2, 3, 4]


def test_load_reads_the_day_files_of_the_branch(tmp_path, monkeypatch):
    remote, work = tmp_path / "remote", tmp_path / "work"
    run = lambda *a, cwd=work: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)
    run("init", "-q", "--bare", str(remote), cwd=tmp_path)
    run("init", "-q", str(work), cwd=tmp_path)
    run("checkout", "-q", "--orphan", "metrics")
    metrics_log.add(work, [comment(1, "2026-10-26T10:00:00Z"), comment(2, "2026-10-27T10:00:00Z")])
    run("add", "status")
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "log")
    run("remote", "add", "origin", str(remote))
    run("push", "-q", "origin", "metrics")
    monkeypatch.setattr(metrics_log, "ROOT", str(work))
    since = datetime.datetime(2026, 10, 26, 12, tzinfo=datetime.timezone.utc)
    assert [c["id"] for c in metrics_log.load(since)] == [2]
    assert metrics_log.load(since, remote="nothing") is None
