"""health.py reads the status comments from their own endpoint, and report.py writes the lane of the run (#1982)."""
import datetime
import subprocess

import health
import metrics_log
import report

SINCE = datetime.datetime(2026, 10, 27, 12, tzinfo=datetime.timezone.utc)
REPORT = {"id": 7, "created_at": "2026-10-27T18:00:00Z", "issue_url": "x/issues/1", "body": "Metrics: ticket #5 · lane haiku"}


def fake_api(path):
    if path.startswith("actions/runs?"):
        return {"workflow_runs": []}
    if path.startswith("issues?state=open&labels="):
        return [{"number": 1}]
    if path.startswith("issues/1/comments?since=2026-10-27T12:00:00Z"):
        return [REPORT]
    return []           # the repository-wide comments miss the report (a cut, #1717)


def test_the_status_comments_come_from_the_status_issue(monkeypatch):
    monkeypatch.setattr(health, "api", fake_api)
    monkeypatch.setattr(metrics_log, "api", fake_api)
    monkeypatch.setattr(metrics_log, "load", lambda since: None)          # no log: the API alone (#1983)
    _, _, status_comments, recent, *_ = health.fetch(SINCE)
    assert status_comments == [REPORT]


def lane_report(capsys):
    report.main(["--text", "x", "--usage", "Usage: u", "--ticket", "1", "--size", "S", "--result", "none"])
    return next(line for line in capsys.readouterr().out.splitlines() if line.startswith("Metrics:"))


def test_the_report_takes_the_lane_from_git_config(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(report, "tool", lambda *a: "")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.chdir(tmp_path)
    assert not lane_report(capsys).endswith("lane haiku")
    subprocess.run(["git", "config", "aoe2mc.lane", "haiku"], check=True)
    assert lane_report(capsys).endswith("· lane haiku")
    assert health.lanes([{"body": lane_report(capsys).replace("0 min", "5 min")}])["haiku"][0] == 1
