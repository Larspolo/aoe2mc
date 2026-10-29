"""Each run names its Claude account in its claims, `Usage:` and `Run:` lines, and the burn is measured per account
(#4236, item 1 of epic #4232, docs/COLLABORATORS.md part 2)."""
import datetime
import os
import subprocess
import sys

import health
import report
import usage

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "claim.py")
NOW = datetime.datetime(2026, 10, 26, 6, 0, tzinfo=datetime.timezone.utc)
RESET = NOW + datetime.timedelta(hours=1)


def run(*a, cwd):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def repo(tmp_path, **config):
    remote, d = tmp_path / "remote.git", tmp_path / "run"
    run("git", "init", "-q", "--bare", str(remote), cwd=tmp_path)
    run("git", "init", "-q", "-b", "run-0", str(d), cwd=tmp_path)
    run("git", "remote", "add", "origin", str(remote), cwd=d)
    for k, v in {"user.name": "t", "user.email": "t@t", **config}.items():
        run("git", "config", k, v, cwd=d)
    return remote, d


def claim_and_beat(remote, d):
    out = []
    for args in (["8"], ["8", "--beat"]):
        assert subprocess.run([sys.executable, TOOL, *args], cwd=d, capture_output=True).returncode == 0
        out.append(run("git", "log", "-1", "--format=%s", "claim/8", cwd=remote))
    return out


def test_claims_and_beats_carry_the_account(tmp_path):
    remote, d = repo(tmp_path, **{"aoe2mc.account": "bob", "aoe2mc.lane": "haiku"})
    claim, beat = claim_and_beat(remote, d)
    assert claim.endswith(" account bob lane haiku") and beat == "Beat #8 by run-0 account bob lane haiku"
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    assert health.count_lanes([f"8 {now} {beat}"], datetime.datetime.now(datetime.timezone.utc)) == {"haiku": 1}


def test_claims_without_an_account_stay_the_same(tmp_path):
    remote, d = repo(tmp_path, **{"aoe2mc.lane": "haiku"})
    claim, beat = claim_and_beat(remote, d)
    assert " account " not in claim and claim.endswith(") lane haiku") and beat == "Beat #8 by run-0 lane haiku"


def test_the_run_line_carries_the_account_of_git_config(tmp_path, monkeypatch):
    run("git", "init", "-q", str(tmp_path), cwd=tmp_path)
    monkeypatch.chdir(tmp_path)
    body = lambda: report.report("x", "Usage: u", [], release="", tokens="T", calls="", run="Run: r", lane="deep")
    assert "Run: r · lane deep" + report.FOOTER in body()
    run("git", "config", "aoe2mc.account", "bob", cwd=tmp_path)
    assert "Run: r · lane deep · account bob" + report.FOOTER in body()


def line(h, used, account=None):
    t = (NOW - datetime.timedelta(hours=h)).timestamp()
    return usage.sample_line({"five_hour": (used, RESET.timestamp(), "allowed")}, t, 10, account=account)


def test_each_account_gets_the_burn_of_its_own_lines(monkeypatch):
    monkeypatch.setattr(health, "first_account", lambda: "lars")     # test data, not the accounts of agent.toml
    lars = [line(h, 0.1 + 0.04 * (5 - h)) for h in range(6)]             # 0.04 per hour by 10 runs: 0.004
    bob = [line(h + 0.5, 0.5 + 0.08 * (5 - h), "bob") for h in range(6)]   # 0.008 in another quota
    assert health.SAMPLE.match(bob[0]) and bob[0].endswith(" · account bob")
    c = [{"body": b} for pair in zip(lars, bob) for b in pair]
    assert abs(health.measured_burn(c, NOW, account="lars") - 0.004) < 1e-9
    assert abs(health.measured_burn(c, NOW, account="bob") - 0.008) < 1e-9
    assert health.measured_burn(c, NOW, account="carol") is None
