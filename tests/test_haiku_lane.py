"""Haiku runs take the tickets with `lane:haiku`; Opus runs take them only when nothing else is ready (#1715)."""
import dashboard
import health
import usage


def issue(n, *names):
    return dict(number=n, title=f"Ticket {n}", labels=[{"name": x} for x in names], body="")


def test_the_haiku_lane_takes_only_its_tickets():
    issues = [issue(1, "P1"), issue(2, "P3", "lane:haiku"), issue(3, "P2", "lane:haiku"), issue(4, "P2", "lane:haiku", "in-progress")]
    assert [i["number"] for i in dashboard.candidates(issues, lane="haiku")] == [3, 2]


def test_an_opus_run_takes_a_lane_ticket_last():
    issues = [issue(1, "P3"), issue(2, "P0", "lane:haiku"), issue(3, "P2")]
    assert [i["number"] for i in dashboard.candidates(issues)] == [3, 1, 2]
    assert [i["number"] for i in dashboard.candidates([issue(2, "P0", "lane:haiku")])] == [2]


def test_the_pacer_gives_the_haiku_task_at_most_the_ready_lane_tickets():
    assert usage.lane_plan(2, 0, 10, 1, 0.25, False) == (2, 1)        # 1 Haiku run (0.25), then 1 Opus run (1.75 left)
    assert usage.lane_plan(0, 0, 10, 5, 0.25, False) == (0, 0)


def test_health_counts_each_lane():
    comments = [
        {"body": "Metrics: ticket #5 · size:S · pr #9 · 10 min · setup 0 min · phases read 1\nTokens: 1.2M eq · x · sinks base 40%"},
        {"body": "Metrics: ticket #6 · size:S · merged · 20 min · setup 0 min · lane haiku\nTokens: 0.8M eq · x · sinks base 50%"},
        {"body": "Metrics: ticket #7 · size:S · blocked · 6 min · setup 0 min · lane haiku"},
    ]
    assert health.lanes(comments) == {"opus": (1, 1, [10.0], [1.2]), "haiku": (2, 1, [20.0, 6.0], [0.8])}
