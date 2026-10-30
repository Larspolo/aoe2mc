"""The "Activity" section of the dashboard (#4725): runs per merged PR and what the runs do, per day."""
import dashboard
import dashboard_data as dd

TOK = "Tokens: 1.00M eq · calls 10 · write 0.1M · peak 50k"
RUN = (f"Did #1.\nMetrics: ticket #1 · size:S · merged · 30 min · setup 1 min · phases read 5 · claim 1 · code 15 · "
       f"verify 4 · ci 0 · conflict 5 · report 0\n{TOK}\n")
COMMENTS = [{"created_at": "2026-10-30T08:00:00Z", "body": RUN},
            {"created_at": "2026-10-30T09:00:00Z", "body": f"No ticket is ready.\n{TOK}\n"},
            {"created_at": "2026-10-30T10:00:00Z", "body": "Process review: fewer conflicts.\n"},
            {"created_at": "2026-10-29T10:00:00Z", "body": RUN},
            {"created_at": "2026-10-29T11:00:00Z", "body": "Not a report."}]


def test_activity_counts_runs_merges_kinds_and_work_per_day():
    got = dd.activity(comments=COMMENTS)
    assert [r["day"] for r in got] == ["2026-10-30", "2026-10-29"]
    assert got[0]["runs"] == 3 and got[0]["merged"] == 1
    assert got[0]["kinds"] == {"ticket": 1, "idle": 1, "review": 1}
    assert got[0]["work"]["tickets"] == 19 and got[0]["work"]["read and triage"] == 6 and got[0]["work"]["conflicts"] == 5
    assert got[1]["runs"] == 1


def test_render_shows_the_activity_section_only_with_data():
    args = ("", [], {}, [], [], [], dashboard.datetime.datetime(2026, 10, 30, tzinfo=dashboard.datetime.timezone.utc))
    body = dashboard.render(*args, nxt=[], insights=dict(lanes={}, sizes={}, days=dd.activity(comments=COMMENTS)))
    assert "### Activity (7 days)" in body
    assert "| 2026-10-30 | 3 | 1 | 3.0 | 1, 1, 1 | tickets 19, read and triage 6, conflicts 5 |" in body
    assert "### Activity" not in dashboard.render(*args, nxt=[], insights=None)
