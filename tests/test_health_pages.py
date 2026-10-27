"""health.fetch() reads all run reports, also on a day with more than 2000 comments (#1985)."""
import datetime
import re

import health

NOW = datetime.datetime(2026, 10, 27, 20, 0, tzinfo=datetime.timezone.utc)


def fake_api(comments):
    """A GitHub fake: `issues/comments` and `issues/1/comments` with since, sort, direction and pages of 100."""
    def api(path):
        if path.startswith("actions/runs?"):
            return {"workflow_runs": []}
        if path.startswith("issues?state=open&labels="):
            return [{"number": 1}]
        m = re.match(r"issues/(?:(\d+)/)?comments\?(.*)", path)
        if m:
            q = dict(p.split("=", 1) for p in m[2].split("&") if p)
            got = [c for c in comments if c["created_at"] >= q.get("since", "")
                   and (m[1] is None or c["issue_url"].endswith(f"/{m[1]}"))]
            got.sort(key=lambda c: c["created_at"], reverse=q.get("direction") == "desc")
            page = int(q["page"])
            return got[(page - 1) * 100:page * 100]
        return []
    return api


def test_the_newest_status_comment_is_read_after_2500_comments(monkeypatch):
    start = NOW - datetime.timedelta(hours=40)
    comments = [{"created_at": f"{start + datetime.timedelta(minutes=i):%Y-%m-%dT%H:%M:%SZ}",
                 "issue_url": f"https://api.github.com/repos/o/r/issues/{1 if i % 5 == 0 else 7}",
                 "body": f"comment {i}"} for i in range(2500)]
    newest = comments[-1 if comments[-1]["issue_url"].endswith("/1") else -5]
    monkeypatch.setattr(health, "api", fake_api(comments))
    runs, jobs, status, recent, prs, issues, events = health.fetch(NOW - datetime.timedelta(hours=24))
    assert newest in status
    assert comments[-1] in recent
