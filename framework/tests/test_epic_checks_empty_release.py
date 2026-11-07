"""A release epic with an empty milestone waits for the roadmap review, not for an epic check (#6069): as an epic check
it was a refill source, so `claim.refill_starved()` was False, the roadmap review (the only source of its scope) waited
for 100 merged PRs, and with no ready ticket nothing merged."""
import claim
import dashboard
import usage

NOW = 1_800_000_000


def release(number=10, version="v0.7.0"):
    return {"number": number, "title": f"Release {version}", "labels": [{"name": "epic"}, {"name": dashboard.RELEASE}],
            "created_at": "2020-01-01T00:00:00Z", "body": ""}


def milestone(open_issues, closed_issues, title="v0.7.0"):
    return {"title": title, "open_issues": open_issues, "closed_issues": closed_issues}


def test_an_empty_milestone_has_no_epic_check():
    assert usage.epic_checks([release()], NOW, lambda: [milestone(0, 0)]) == []
    assert usage.epic_checks([release()], NOW, lambda: [milestone(3, 0, "v0.6.0")]) == []   # no milestone of v0.7.0


def test_a_milestone_with_closed_issues_only_keeps_its_epic_check():
    assert usage.epic_checks([release()], NOW, lambda: [milestone(0, 16)]) == [10]          # the check closes it (#6024)


def test_a_read_error_keeps_the_epic_check(capsys):
    def fail():
        raise OSError("GitHub is down")
    assert usage.epic_checks([release()], NOW, fail) == [10]
    assert "GitHub is down" in capsys.readouterr().err


def test_the_milestones_are_read_once_and_only_for_a_release_epic():
    reads = []
    other = {"number": 9, "labels": [{"name": "epic"}], "created_at": "2020-01-01T00:00:00Z", "body": ""}
    assert usage.epic_checks([other], NOW, lambda: reads.append(1) or []) == [9]
    assert reads == []
    assert usage.epic_checks([release(10), release(11, "v0.8.0"), other], NOW,
                             lambda: reads.append(1) or [milestone(0, 0), milestone(0, 2, "v0.8.0")]) == [11, 9]
    assert reads == [1]


def test_an_empty_release_milestone_starves_the_refill(monkeypatch):
    monkeypatch.setattr(usage, "read_usage", lambda: {"five_hour": (0.05, 0, "allowed")})
    monkeypatch.setattr(usage, "read_status", lambda: ([], ""))
    monkeypatch.setattr(usage, "burns", lambda comments, burn=None: (0.01, None))
    monkeypatch.setattr(usage, "release_due", lambda: [])
    monkeypatch.setattr(usage, "free_sources", lambda: [])
    monkeypatch.setattr(usage, "target_runs", lambda *a, **k: 9)
    monkeypatch.setattr(dashboard, "orphans", lambda issues: [])
    for counts, want in (((0, 0), True), ((0, 16), False)):
        pages = {"issues?state=open": [release()], "milestones?state=all": [milestone(*counts)]}
        monkeypatch.setattr(dashboard, "pages", lambda path, pages=pages: pages[path])
        assert claim.refill_starved() is want, counts
