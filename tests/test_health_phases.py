"""framework/tools/health.py: phase minutes, quota per merged PR, release per 7-day quota and weak spots (#899)."""
import datetime

import health
import release
import usage

SINCE = datetime.datetime(2026, 10, 26, 0, 0, tzinfo=datetime.timezone.utc)
U = "https://api.github.com/repos/Larspolo/aoe2mc/issues/"


def test_phase_minutes_and_old_lines():
    comments = [{"body": "Run 1\nMetrics: ticket #5 · size:S · merged · 30 min · setup 1 min · checks 2 · checks 6 min · "
                         "time sinks: none · phases read 4 · claim 1 · code 12 · verify 8 · ci 2 · conflict 0 · report 3"},
                {"body": "Metrics: ticket #6 · size:M · merged · 50 min · setup 0 min · checks 1 · checks 9 min · "
                         "time sinks: none"},                                       # an old line: no phases
                {"body": "Metrics: ticket #7 · phases read 1.5 · code 3 · verify 1"}, {"body": None}]
    ph = health.phase_minutes(comments)
    assert ph == {"read": 5.5, "claim": 1, "code": 15, "verify": 9, "ci": 2, "conflict": 0, "report": 3}
    assert health.setup_minutes(comments) == [1.0, 0.0]


def test_quota_per_merge():
    t = lambda h: SINCE + datetime.timedelta(hours=h)
    r1, r2 = t(5), t(10)
    s = [(t(1), 0.10, r1, 3), (t(2), 0.30, r1, 3), (t(6), 0.05, r2, 3), (t(7), 0.25, r2, 3)]
    assert abs(health.quota_per_merge(s, 4) - 0.1) < 1e-9                   # (0.2 + 0.2) / 4; the reset is no rise
    assert health.quota_per_merge(s, 0) is None


def test_week_and_release_from_usage_lines():
    line = usage.sample_line({"five_hour": (0.3, 0, "allowed"), "seven_day": (0.56, 0, "allowed")}, 0, 4, 61.24)
    assert line.endswith("· runs 4 · week 56.0% · release 61.2% · week resets 1970-01-01T00:00:00Z")
    assert health.samples([{"body": line}])[0][1:] == (0.3, datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc), 4)
    old = usage.sample_line({"five_hour": (0.3, 0, "allowed")}, 3600, 4)
    pts = health.weekly([{"body": line}, {"body": old}, {"body": line.replace("1970-01-01T00:00:00Z", "1970-01-01T05:00:00Z", 1)
                                                         .replace("week 56.0%", "week 60.0%").replace("61.2%", "63.2%")}])
    assert [p[1:] for p in pts] == [(56.0, 61.2), (60.0, 63.2)]
    assert health.release_per_week(pts) == (0.5, 61.2, 63.2)                # 2 points per 4 % of the week
    assert health.release_per_week(pts[:1]) is None


def test_release_total():
    result = {1: {"C": (80, 8, 1, 1, 0)}, 2: {"C": (50, 2, 2, 0, 0)}}
    assert release.total(result) == 100 * 10 / 14
    assert release.total({}) == 100.0


def test_weak_spots():
    bug = lambda n, body: {"number": n, "title": "Fix x", "body": body, "created_at": "2026-10-26T05:00:00Z",
                           "labels": [{"name": "bug"}]}
    issues = [bug(20, "Found in PR #11."), bug(21, "The check #15 found it."), bug(22, "Old PR #3."),
              {"number": 15, "title": "Check the gathering", "body": "", "created_at": "2026-10-20T00:00:00Z", "labels": []},
              {"number": 11, "title": "PR", "body": "", "created_at": "2026-10-26T01:00:00Z", "labels": [],
               "pull_request": {}}]
    prs = [{"number": 11, "merged_at": "2026-10-26T02:00:00Z"}, {"number": 3, "merged_at": "2026-10-20T02:00:00Z"}]
    events = [{"event": "reopened", "actor": {"login": "Larspolo"}, "created_at": "2026-10-26T03:00:00Z"},
              {"event": "reopened", "actor": {"login": "someone"}, "created_at": "2026-10-26T03:00:00Z"},
              {"event": "closed", "actor": {"login": "Larspolo"}, "created_at": "2026-10-26T03:00:00Z"}]
    runs = [{"name": "CI", "event": "schedule", "conclusion": "failure", "run_started_at": "2026-10-26T01:00:00Z"},
            {"name": "CI", "event": "push", "conclusion": "failure", "run_started_at": "2026-10-26T01:00:00Z"}]
    assert health.weak_spots(issues, events, prs, runs, SINCE) == {"reopened": 1, "rework": 1, "check bugs": 1,
                                                                    "red nights": 1}
    text = health.report(SINCE, runs, [], [{"body": "Metrics: ticket #5 · phases read 2 · code 6"}], [], prs, [],
                         issues=issues, issue_events=events)
    assert "Phases (min, share of the Metrics lines with phases): read 2.0 (25%)" in text
    assert "Weak spots: reopened 1, rework 1, check bugs 1, red nights 1" in text
