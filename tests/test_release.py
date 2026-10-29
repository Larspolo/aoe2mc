"""tools/release.py: progress of each goal toward its release bar with the rules of #878 (#879)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import release  # noqa: E402

ROADMAP = """# Roadmap
## 1. Convert maps
- [x] `convert:terrain` Terrain (#10)
- [ ] `convert:minimap` A map item
## 2. Play AoE2 in Minecraft
- [x] `play:gather` Gather
- [ ] `play:fight` Fights (epic #20)
- [ ] `play:tech` Technologies
- [ ] `play:monks` Monks
"""
RELEASE = """# Release bar
Bug reserve: 0.3
## Rules
| `x:y` | B | | | |
## Convert maps
| id | milestone | estimate | check | ticket |
|---|---|---|---|---|
| `convert:terrain` | B | | | |
| `convert:minimap` | A | | | |
| `convert-check-maps` | B | 5 | 20 maps convert | #40 |
## Play AoE2
| id | milestone | estimate | check | ticket |
|---|---|---|---|---|
| `play:gather` | B | | | |
| `play:fight` | B | | | |
| `play:tech` | A | 8 | | |
| `play-check-game` | B | 2 | A full game | |
"""


def epic(n, state, total, done, key=None):
    return {"number": n, "state": state, "body": f"Roadmap: `{key}`" if key else "",
            "sub_issues_summary": {"total": total, "completed": done}}


EPICS = [epic(10, "closed", 4, 4), epic(11, "closed", 6, 6), epic(12, "closed", 7, 7),     # median 6
         epic(20, "open", 9, 3), epic(30, "open", 2, 1, "convert:minimap")]


def test_parse_the_roadmap_and_the_release_bar():
    f = release.roadmap(ROADMAP)
    assert f["convert:terrain"] == (1, True, {10}) and f["play:fight"] == (2, False, {20})
    assert f["play:monks"] == (2, False, set())
    share, rows = release.release(RELEASE)
    assert share == 0.3 and (1, "convert-check-maps", "B", 5, 40) in rows and (2, "play:tech", "A", 8, None) in rows
    assert all(r[1] != "x:y" for r in rows)                        # the rules section has no items


def test_progress_follows_the_rules_of_878():
    share, rows = release.release(RELEASE)
    r = release.progress(release.roadmap(ROADMAP), rows, share, EPICS)
    # Convert: terrain done 4 (epic #10); minimap open: max(2, median 6) - 1 = 5 left, done 1; check: 5 left.
    assert r[1]["B"] == (44, 4, 0, 5, 0)                              # 4 / (4 + 5)
    assert r[1]["A"] == r[1]["C"] == (29, 5, 5, 5, 2)                 # 5 / (5 + 5 + 5 + ceil(1.5))
    # Play: gather checked without epic: 6 done; fight open: 9 - 3 = 6 left; tech: 8 left; monks (no row): C, 6 left.
    assert r[2]["B"] == (47, 9, 6, 2, 2)                              # 9 / (9 + 6 + 2 + 2)
    assert r[2]["A"] == (30, 9, 14, 2, 5)                             # 9 / (9 + 14 + 2 + ceil(4.2))
    assert r[2]["C"] == (24, 9, 20, 2, 6)


def test_a_closed_check_ticket_counts_as_done():
    share, rows = release.release(RELEASE)
    r = release.progress(release.roadmap(ROADMAP), rows, share, EPICS, closed={40})
    assert r[1]["B"] == (100, 9, 0, 0, 0)


def test_lines():
    out = release.lines({1: {"C": (29, 5, 5, 5, 2), "A": (29, 5, 5, 5, 2), "B": (44, 4, 0, 5, 0)}})
    assert out == ["Convert maps: C 29 % (12 left = 5 + 5 + 2) · A 29 % (12 left = 5 + 5 + 2) · B 44 % (5 left = 0 + 5 + 0)"]


def test_each_roadmap_feature_has_a_row_of_its_goal():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "steering", "project", "ROADMAP.md")) as f:
        features = release.roadmap(f.read())
    with open(os.path.join(root, "steering", "project", "RELEASE.md")) as f:
        _, rows = release.release(f.read())
    keys = {r[1]: r[0] for r in rows if ":" in r[1]}
    assert keys == {k: g for k, (g, _, _) in features.items()}
    assert all("-check-" in r[1] for r in rows if ":" not in r[1])
