"""The release focus (owner, 2026-11-01): until the next release, a roadmap feature outside the milestones of the line
"Release focus: X" of steering/project/RELEASE.md waits. It is no refill source, and `release.py` counts it."""
import dashboard
import release
import usage

ROADMAP = """## 1. Convert maps
- [ ] `convert:core` A milestone A feature
- [ ] `convert:extra` A milestone C feature
- [ ] `convert:norow` A feature with no row: milestone C
- [x] `convert:done` A done milestone C feature
"""
ROWS = [(1, "convert:core", "A", None, None), (1, "convert:extra", "C", 3, None), (1, "convert:done", "C", None, None)]


def write(tmp_path, text):
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "coverage.md").write_text("")
    (tmp_path / "steering" / "project").mkdir(parents=True, exist_ok=True)
    (tmp_path / "steering" / "project" / "RELEASE.md").write_text(text)


def test_focus_reads_the_line(tmp_path):
    assert release.focus(tmp_path) == "C"                    # no file
    write(tmp_path, "# Release bar\n\nBug reserve: 0.3\n")
    assert release.focus(tmp_path) == "C"                    # no line
    write(tmp_path, "# Release bar\n\nRelease focus: A\n")
    assert release.focus(tmp_path) == "A"


def test_waiting_features():
    features = release.roadmap(ROADMAP)
    assert release.waiting(features, ROWS, "A") == ["convert:extra", "convert:norow"]
    assert release.waiting(features, ROWS, "B") == ["convert:core", "convert:extra", "convert:norow"]
    assert release.waiting(features, ROWS, "C") == []


def test_a_feature_outside_the_focus_is_no_source(tmp_path, monkeypatch):
    features = release.roadmap(ROADMAP)
    monkeypatch.setattr(release, "load", lambda: (features, 0, ROWS, []))
    monkeypatch.setattr(dashboard, "api", lambda path: dict(state="closed", labels=[]))
    write(tmp_path, "Release focus: C\n")
    assert usage.free_sources(tmp_path) == ["3 roadmap features with no epic"]
    write(tmp_path, "Release focus: A\n")
    assert usage.free_sources(tmp_path) == ["1 roadmap features with no epic"]      # only convert:core
    del features["convert:core"]
    assert usage.free_sources(tmp_path) == []
