"""The owner's dashboard shows the Haiku lane (#1715, #1727): its tickets and its runs."""
import os

import dashboard_data as dd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = open(os.path.join(ROOT, "tools", "dashboard_artifact", "index.html")).read()


def test_usage_rows_count_all_runs_and_the_haiku_runs(monkeypatch):
    # The pacing counts a Haiku run as a part of an Opus run; the dashboard shows the runs themselves.
    body = "Usage: 2026-10-27T16:00:00Z · usage 6.0% · resets 2026-10-27T20:50:00Z · runs 5 · week 5.0% · haiku 2"
    monkeypatch.setattr(dd.health, "status_comments", lambda hours: [{"body": body}])
    row = dd.usage()[0]
    assert (row["runs"], row["haiku"]) == (5, 2)


def test_tickets_have_the_haiku_lane():
    issue = {"number": 1, "title": "Train X at Y", "state": "open", "created_at": "2026-10-27T10:00:00Z",
             "closed_at": None, "labels": [{"name": "lane:haiku"}, {"name": "size:S"}]}
    assert dd.tickets([issue])[0]["haiku"] and not dd.tickets([dict(issue, labels=[])])[0]["haiku"]


def test_the_page_reads_the_lane_columns():
    cols = dd.page_columns(PAGE)
    assert "haiku" in cols["tickets"] and "haiku" in cols["usage"]

