"""A sub-issue of an epic with `after-release` or `muted` is no ticket candidate (#5169)."""
import dashboard

URL = "https://api.github.com/repos/o/r/issues/"


def issue(n, *names, parent=None):
    i = {"number": n, "title": f"Ticket {n}", "body": "", "labels": [{"name": x} for x in ("P2", "size:S") + names]}
    if parent:
        i["parent_issue_url"] = URL + str(parent)
    return i


def test_the_sub_issues_of_a_parked_epic_are_no_candidates():
    issues = [issue(1, "epic", dashboard.AFTER), issue(2, "epic", dashboard.MUTED), issue(3, "epic"),
              issue(4, parent=1), issue(5, parent=2), issue(6, parent=3), issue(7, parent=99), issue(8)]
    assert [i["number"] for i in dashboard.candidates(issues, reserved=())] == [6, 7, 8]
