"""framework/tools/ship_pr.py --ci --pr-branch B: a takeover waits for the quick CI of the PR of another run (#5014)."""
import sys

sys.path.insert(0, "tools")
import ship_pr  # noqa: E402


def run(monkeypatch, argv, prs):
    asked, waited = [], []
    monkeypatch.setattr(ship_pr.dashboard, "api", lambda path, *a: asked.append(path) or prs)
    monkeypatch.setattr(ship_pr, "ci", lambda number, sha, deadline: waited.append((number, sha)) or 0)
    monkeypatch.setattr(ship_pr, "git", lambda *a: type("R", (), {"stdout": "session-branch\n"})())
    return ship_pr.main(argv), asked, waited


def test_the_pr_branch_gives_the_pr_and_its_head(monkeypatch):
    rc, asked, waited = run(monkeypatch, ["7", "--ci", "--pr-branch", "claude/other-run"], [{"head": {"sha": "abc123"}}])
    assert rc == 0
    assert asked == [f"pulls?head={ship_pr.CONFIG['repo'].split('/')[0]}:claude/other-run&state=open"]
    assert waited == [(7, "abc123")]


def test_without_the_option_the_current_branch_and_a_hint(monkeypatch, capsys):
    rc, asked, waited = run(monkeypatch, ["7", "--ci"], [])
    assert rc == 4 and waited == []
    assert asked[0].endswith(":session-branch&state=open")
    assert "--pr-branch" in capsys.readouterr().out
