"""Opus runs never take the tickets of a reserved lane (`reserved` in `[pacing]` of agent.toml, #1994)."""
import dashboard


def issue(n, *names):
    return {"number": n, "title": f"Ticket {n}", "body": "", "labels": [{"name": x} for x in ("P2", "size:S") + names]}


ISSUES = [issue(1, "lane:haiku"), issue(2), issue(3, "lane:haiku")]


def test_opus_runs_skip_the_tickets_of_a_reserved_lane():
    assert [i["number"] for i in dashboard.candidates(ISSUES, reserved=("haiku",))] == [2]
    assert [i["number"] for i in dashboard.candidates(ISSUES, lane="haiku", reserved=("haiku",))] == [1, 3]


def test_without_a_reserved_lane_the_lane_tickets_come_last():
    assert [i["number"] for i in dashboard.candidates(ISSUES, reserved=())] == [2, 1, 3]
