"""The data files of the owner's dashboard artifact have the columns that its page reads (#982)."""
import json
import os

import dashboard_data as dd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = open(os.path.join(ROOT, "tools", "dashboard_artifact", "index.html")).read()


def label(*names):
    return [{"name": n} for n in names]


ISSUES = [
    {"number": 5, "title": "Epic", "state": "open", "created_at": "2026-10-25T10:00:00Z", "closed_at": None,
     "labels": label("epic", "P2", "feature", "size:L"), "body": "Roadmap: `play-cheats`",
     "sub_issues_summary": {"completed": 1, "total": 3}},
    {"number": 6, "title": "Fix", "state": "closed", "created_at": "2026-10-25T11:00:00Z",
     "closed_at": "2026-10-25T12:00:00Z", "labels": label("P1", "bug", "size:S", "in-progress"), "body": None},
    {"number": 7, "title": "A PR", "state": "closed", "pull_request": {}, "labels": [], "created_at": "", "closed_at": ""},
]
PULLS = [
    {"number": 8, "title": "Fix", "head": {"ref": "claude/x"}, "created_at": "2026-10-25T11:00:00Z",
     "merged_at": "2026-10-25T11:30:00Z"},
    {"number": 9, "title": "Closed", "head": {"ref": "claude/y"}, "created_at": "2026-10-25T11:00:00Z", "merged_at": None},
]
ROADMAP = """# Roadmap

## 2. Play AoE2 in Minecraft

- [x] `play-gather` Gather resources (epic #138)
- [ ] `play-cheats` The `cheat` codes (#820, #967)

## Notes

- [ ] `not-a-feature` Text
"""
RELEASE = """Bug reserve: 0.3

## Play AoE2

| Key | Milestone | Estimate | Title | Ticket |
|---|---|---|---|---|
| `play-cheats` | B | 4 | Cheats |  |
| `play-check-cheats` | A | 1 | Check the cheats | #965 |
"""


def test_merged_prs_keep_only_merges_with_the_minutes_open():
    rows = dd.merged_prs(PULLS)
    assert [r["number"] for r in rows] == [8] and rows[0]["minutes_open"] == 30.0
    assert set(rows[0]) >= {"number", "title", "branch", "merged_at", "minutes_open"}


def test_tickets_have_the_priority_and_flow_columns():
    rows = dd.tickets(ISSUES)
    assert [r["number"] for r in rows] == [5, 6]
    assert rows[0]["priority"] == "P2" and rows[0]["epic"] and rows[0]["subs_total"] == 3
    assert rows[1]["priority"] == "P1" and rows[1]["size"] == "S" and rows[1]["in_progress"]
    # The bands of "Open tickets over time" (page version 7) read the priority column.
    assert "open_p0" in PAGE and "r.priority" in PAGE
    assert set(rows[0]) >= {"state", "created_at", "closed_at", "kind", "status_issue", "needs_human", "muted"}


def test_epics_read_the_roadmap_key():
    rows = dd.epics(ISSUES)
    assert rows == [dict(number=5, title="Epic", state="open", closed_at="", key="play-cheats", subs_done=1, subs_total=3)]


def test_roadmap_reads_the_features_of_the_goals_only():
    rows = dd.roadmap(ROADMAP)
    assert [(r["goal"], r["key"], r["checked"], r["refs"]) for r in rows] == [
        ("play", "play-gather", True, "138"), ("play", "play-cheats", False, "820 967")]
    assert rows[1]["feature"] == "The cheat codes"


def test_release_bar_has_the_rows_and_a_reserve_for_each_goal():
    rows = dd.release_bar(RELEASE)
    assert [(r["id"], r["kind"], r["level"], r["estimate"], r["ticket"]) for r in rows[:2]] == [
        ("play-cheats", "feature", "B", 4.0, None), ("play-check-cheats", "check", "A", 1.0, "965")]
    reserve = [r for r in rows if r["kind"] == "reserve"]
    assert len(reserve) == 4 and {r["share"] for r in reserve} == {0.3}


def test_usage_reads_the_usage_lines(monkeypatch):
    body = "Usage: 2026-10-26T16:45:08Z · usage 6.0% · resets 2026-10-26T21:30:00Z · runs 4 · week 5.0%"
    monkeypatch.setattr(dd.health, "status_comments", lambda hours: [{"body": body}])
    assert dd.usage() == [dict(at="2026-10-26T16:45:08Z", usage=0.06, resets="2026-10-26T21:30:00Z", runs=4, haiku=0,
                                week=0.05, week_resets=None, track=None)]


def test_main_writes_the_eight_files(tmp_path, monkeypatch):
    monkeypatch.setattr(dd, "pages", lambda path: ISSUES if path.startswith("issues") else PULLS)
    monkeypatch.setattr(dd, "usage", lambda: [])
    monkeypatch.setattr(dd, "tokens", lambda: [])
    monkeypatch.setattr(dd, "accounts", lambda: [])
    monkeypatch.setattr(dd, "reviews", lambda merges: [])
    dd.main(str(tmp_path))
    assert sorted(os.listdir(tmp_path)) == sorted(dd.DATASETS.values())
    setup = json.load(open(tmp_path / "aoe2mc-setup.json"))
    assert setup and set(setup[0]) == {"part", "group", "when", "does", "where"}
