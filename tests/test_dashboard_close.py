"""A ticket with the label `close` waits only for close.yml: it is no candidate (#2920)."""
import dashboard


def issue(n, *names):
    return dict(number=n, title=f"Ticket {n}", labels=[{"name": x} for x in ("P2",) + names], body="")


def test_close_is_no_candidate():
    assert [i["number"] for i in dashboard.candidates([issue(1), issue(2, "close")])] == [1]


def test_same_ticket_without_close_is_a_candidate():
    assert [i["number"] for i in dashboard.candidates([issue(2)])] == [2]
