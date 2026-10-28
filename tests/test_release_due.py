"""tools/release.py `due()`: the release checks that can start and have no ticket, and their section in
tools/cycle_start.py (#3342)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import cycle_start  # noqa: E402
import release  # noqa: E402

ROADMAP = """# Roadmap
## 1. Convert maps
- [x] `convert:terrain` Terrain (#10)
## 2. Play AoE2 in Minecraft
- [x] `play:gather` Gather
- [ ] `play:fight` Fights (epic #20)
- [ ] `play:tech` Technologies
"""
RELEASE = """# Release bar
Bug reserve: 0.3
## Rules
| `x:y` | B | | | |
## Convert maps
| id | milestone | estimate | check | ticket |
|---|---|---|---|---|
| `convert:terrain` | B | | | |
| `convert-check-maps` | B | 5 | 20 maps convert | #40 |
## Play AoE2
| id | milestone | estimate | check | ticket |
|---|---|---|---|---|
| `play:gather` | B | | | |
| `play:fight` | B | | | |
| `play:tech` | A | 8 | | |
| `play-check-game` | B | 2 | A full game | |
| `play-check-tech` | A | 1 | All technologies | |
"""


def epic(n, state, total, done):
    return {"number": n, "state": state, "body": "", "sub_issues_summary": {"total": total, "completed": done}}


def ids(epics):
    _, rows = release.release(RELEASE)
    return [r[1] for r in release.due(release.roadmap(ROADMAP), rows, epics)]


def test_a_check_with_no_ticket_is_due_when_its_milestone_has_no_feature_left():
    # play:fight (B) is done: its epic closed. play:tech (A) is still to do, so only the B check is due.
    assert ids([epic(20, "closed", 6, 6)]) == ["play-check-game"]


def test_no_check_is_due_while_a_feature_of_its_milestone_is_left():
    assert ids([epic(20, "open", 6, 3)]) == []


def test_a_check_with_a_ticket_is_never_due():
    # convert:terrain is checked, so milestone B of goal 1 has 0 features left, but its check has ticket #40.
    assert "convert-check-maps" not in ids([epic(20, "closed", 6, 6)])


def test_the_text_names_the_goal_and_the_milestone():
    rows = [(2, "play-check-game", "B", 2, None)]
    assert release.due_lines(rows) == ["play-check-game (Play AoE2, B)"]


def test_cycle_start_shows_the_due_checks(monkeypatch, capsys):
    monkeypatch.setattr(release, "load", lambda: (release.roadmap(ROADMAP), 0.3, release.release(RELEASE)[1],
                                                  [epic(20, "closed", 6, 6)]))
    checks = cycle_start.due_checks()
    assert checks == ["play-check-game (Play AoE2, B)"]
    cycle_start.section("Release checks (no ticket, make them in the refill)", checks)
    assert "Release checks (no ticket, make them in the refill): play-check-game" in capsys.readouterr().out


def test_cycle_start_prints_no_section_when_the_read_fails(monkeypatch):
    def fail():
        raise OSError("no access")
    monkeypatch.setattr(release, "load", fail)
    assert cycle_start.due_checks() == []
