"""The "Releases" section of the status issue (owner, 2026-11-01): the progress of the next release (the release
focus of steering/project/RELEASE.md) and of the full roadmap, for each game goal."""
import datetime

import dashboard
import release

NOW = datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc)
# {goal: {milestone: (percent, done, features left, checks left, reserve)}}, as release.progress()
RESULT = {1: {"C": (75, 30, 8, 0, 2), "A": (100, 20, 0, 0, 0), "B": (100, 10, 0, 0, 0)},
          2: {"C": (50, 10, 6, 2, 2), "A": (80, 8, 1, 0, 1), "B": (100, 5, 0, 0, 0)},
          4: {"C": (100, 3, 0, 0, 0), "A": (100, 3, 0, 0, 0)}}


def test_releases_rows():
    rows = release.releases(RESULT, "A")
    assert [r[0] for r in rows] == ["Next release (focus A)", "Full roadmap (C)"]
    name, goals, pct, left = rows[0]
    assert list(goals) == [release.GOALS[1], release.GOALS[2]]          # goal 4 is no game goal
    assert goals[release.GOALS[2]] == (80, 2) and left == 2
    assert pct == release.total(RESULT, "A")
    assert rows[1][3] == 10 + 10
    assert len(release.releases(RESULT, "C")) == 1                      # no focus: one release


def test_the_status_issue_shows_each_release():
    data = dict(rows=release.releases(RESULT, "A"), waiting=7)
    body = dashboard.render("", [], {}, [], [], [], NOW, nxt=[], releases=data)
    section = body.split("### Releases\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert section[0] == f"| Release | {release.GOALS[1]} | {release.GOALS[2]} | All |"
    assert section[2].startswith("| Next release (focus A) | 100 % (0 left) | 80 % (2 left) |")
    assert section[3].startswith("| Full roadmap (C) | 75 % (10 left) | 50 % (10 left) |")
    assert "7 roadmap features" in section[4]
    assert "### Releases" not in dashboard.render("", [], {}, [], [], [], NOW, nxt=[])
