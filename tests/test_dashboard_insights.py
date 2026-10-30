"""The "Insights" section of the dashboard (#4646): usage per lane, per ticket size and the top sinks."""
import dashboard
import dashboard_data as dd

TOK = ("Tokens: 2.00M eq · calls 74 · write 0.11M · read 6.16M · out 0.02M · cost $2.56 · peak 119k · base 43k (repo 8k)"
       " · verify wait 10.6m 5x · force 0 · sinks base 40%, Bash sed 10%")
REPORT = ("Did #1 and #2.\n"
          "Metrics: ticket #1 · size:S · merged · 0 min · setup 1 min\n"
          "Metrics: ticket #2 · size:M · none · 23 min · setup 2 min\n"
          f"{TOK}\nRun: 2026-10-30 · lane haiku\n")


def test_insights_split_the_usage_by_lane_size_and_sink():
    comments = [{"created_at": "2026-10-30T08:00:00Z", "body": REPORT},
                {"created_at": "2026-10-30T09:00:00Z", "body": TOK.replace("2.00M", "1.00M")},
                {"created_at": "2026-10-30T10:00:00Z", "body": "No report lines."}]
    got = dd.insights(comments=comments)
    assert got["lanes"] == {"haiku": dict(runs=1, eq=2.0, merged=1), "opus": dict(runs=1, eq=1.0, merged=0)}
    assert got["sizes"] == {"S": dict(tickets=1, merged=1, eq=1.0), "M": dict(tickets=1, merged=0, eq=1.0)}
    assert [k for k, _ in got["sinks"]] == ["base", "Bash sed"] and abs(got["sinks"][0][1] - 1.2) < 1e-9


def test_render_shows_the_insights_section_only_with_data():
    args = ("", [], {}, [], [], [], dashboard.datetime.datetime(2026, 10, 30, tzinfo=dashboard.datetime.timezone.utc))
    body = dashboard.render(*args, nxt=[], insights=dd.insights(comments=[{"body": REPORT}]))
    assert "### Insights (7 days)" in body and "| haiku | 1 | 2.0 | 1 | 2.00 |" in body and "Top costs (M eq): base 0.8" in body
    assert "### Insights" not in dashboard.render(*args, nxt=[], insights=None)
