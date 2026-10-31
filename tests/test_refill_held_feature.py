"""A roadmap feature that the owner holds is no refill source (#5301): `convert:export` named the `after-release`
owner ticket #4198 (no `epic` label), and the pacer started deep refill runs that found no work."""
import dashboard
import release
import usage

ROADMAP = """## 1. Convert maps
- [ ] `convert:held` Held by the owner (#41, after the release)
- [ ] `convert:muted` Muted by the owner (#42)
- [ ] `convert:plain` Named in a plain ticket (#43, #44)
"""
ISSUES = {41: ["feature", dashboard.AFTER], 42: [dashboard.MUTED], 43: ["feature"], 44: [dashboard.AFTER]}
STATES = {44: "closed"}


def issue(path):
    n = int(path.rsplit("/", 1)[1])
    return dict(number=n, state=STATES.get(n, "open"), labels=[{"name": x} for x in ISSUES[n]])


def test_a_held_feature_is_no_source(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "coverage.md").write_text("")
    features = release.roadmap(ROADMAP)
    monkeypatch.setattr(release, "load", lambda: (features, 0, [], []))
    monkeypatch.setattr(dashboard, "api", issue)
    assert usage.free_sources(tmp_path) == ["1 roadmap features with no epic"]      # only convert:plain
    del features["convert:plain"]
    assert usage.free_sources(tmp_path) == []
