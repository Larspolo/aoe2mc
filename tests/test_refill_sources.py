"""The pacer starts a refill run with R < N only when the refill has a source (#3560): a deep run with R = 34 and N = 40
found every epic covered, every roadmap feature with an epic, no fallback and no due review, and made no ticket."""
import claim
import release
import usage

EPIC = dict(number=9, labels=[{"name": "epic"}], body="Roadmap: `play:x`", sub_issues_summary=dict(total=4, completed=1))
COVERAGE = """| Group | Types | Own design or mapping | Default infantry | Fallback |
|---|---|---|---|---|
| Buildings | 243 | 243 | 0 | {} |
| Other objects | 397 | 397 | 0 | 0 |

| Name | Result | Fallback |
|---|---|---|
| RUINS | ruins (in place_objects) | no |
"""
ROADMAP = """## 2. Play AoE2 in Minecraft (`game/`)
- [x] `play:a` Done
- [ ] `play:x` Has an epic by its key
- [ ] `play:y` Has an epic by its number (#7)
{}
## 4. The agent system
- [ ] `system:z` Goal 4 takes no turn
"""


def test_no_refill_run_below_the_target_without_a_source():
    assert usage.refill_need(34, 40, [EPIC]) == ""
    assert usage.refill_need(34, 40, [EPIC], lambda: [], lambda: [], lambda: []) == ""


def test_a_source_gives_the_refill_runs():
    assert usage.refill_need(34, 40, [EPIC], free=lambda: ["2 fallbacks"]) == "ready 34 < target 40: 2 fallbacks"
    assert usage.refill_need(34, 40, [EPIC], free=lambda: ["read error"]) == "ready 34 < target 40: read error"
    assert usage.refill_need(42, 40, [EPIC], free=lambda: ["2 fallbacks"]) == ""                  # R >= N: no refill


def test_a_due_review_gives_a_deep_run_also_at_the_target():
    assert usage.refill_need(42, 40, [EPIC], reviews=lambda: ["roadmap review"]) == "roadmap review due"
    assert usage.refill_need(3, 40, [], reviews=lambda: ["process review", "roadmap review"]) == \
        "process review and roadmap review due"


def write(tmp_path, fallbacks=0):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "coverage.md").write_text(COVERAGE.format(fallbacks))
    return release.roadmap(ROADMAP.format(""))


def test_free_sources_reads_the_roadmap_and_the_coverage(tmp_path, monkeypatch):
    epics = [dict(number=7, state="open", body=""), dict(number=9, state="closed", body="Roadmap: `play:x`")]
    features = write(tmp_path)
    monkeypatch.setattr(release, "load", lambda: (features, 0, [], epics))
    assert usage.free_sources(tmp_path) == []
    features.update(release.roadmap("## 3. Replay\n- [ ] `replay:new` A new feature"))
    (tmp_path / "docs" / "coverage.md").write_text(COVERAGE.format(3))
    assert usage.free_sources(tmp_path) == ["1 roadmap features with no epic", "3 fallbacks"]


def test_a_read_error_counts_as_a_source(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "load", lambda: 1 / 0)
    assert usage.free_sources(tmp_path) == ["read error"]
    monkeypatch.setattr(claim, "review_slot", lambda kind, remote="origin", **_: claim.fail("GitHub API failed"))
    assert usage.due_reviews() == ["process review", "roadmap review"]


def test_a_taken_review_lock_is_not_due(monkeypatch):
    monkeypatch.setattr(claim, "review_slot", lambda kind, remote="origin", **_: ("100pr-none-1", 100))
    taken = type("R", (), {"stdout": "abc\trefs/heads/claim/roadmap-100pr-none-1\n"})
    monkeypatch.setattr(claim, "git", lambda *a, **k: taken if "roadmap" in a[-1] else type("R", (), {"stdout": ""}))
    assert usage.due_reviews() == ["process review"]
