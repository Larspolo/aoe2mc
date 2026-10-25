"""tools/claim.py: a ticket claim through a git ref, against a local bare repository (no network)."""
import os
import subprocess
import sys

import pytest

import claim

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "claim.py")


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True).stdout


@pytest.fixture
def clones(tmp_path):
    """A bare remote and three clones on the branches run-0, run-1, run-2."""
    remote = tmp_path / "remote.git"
    run("git", "init", "-q", "--bare", str(remote), cwd=tmp_path)
    out = []
    for i in range(3):
        d = tmp_path / f"run{i}"
        run("git", "init", "-q", "-b", f"run-{i}", str(d), cwd=tmp_path)
        run("git", "remote", "add", "origin", str(remote), cwd=d)
        for k, v in (("user.name", "t"), ("user.email", "t@t")):
            run("git", "config", k, v, cwd=d)
        out.append(d)
    return out


def tool(d, *args):
    return subprocess.run([sys.executable, TOOL, *args], cwd=d, capture_output=True, text=True)


def test_one_claim_wins_at_the_same_time(clones):
    procs = [subprocess.Popen([sys.executable, TOOL, "7"], cwd=d, stdout=subprocess.PIPE, text=True)
             for d in clones]
    codes = sorted(p.wait() for p in procs)
    assert codes == [0, 1, 1]
    assert list(claim.refs(7, str(clones[0] / ".." / "remote.git"))) == [1]


def test_release_and_takeover(clones, monkeypatch):
    a, b, c = clones
    assert tool(a, "5").returncode == 0
    assert tool(b, "5").returncode == 1                         # owned by run-0
    assert tool(b, "5", "--release").returncode != 0            # not the claim of run-1
    assert tool(a, "5", "--release").stdout.strip() == "released claim/5"
    assert tool(b, "5").stdout.strip() == "claimed claim/5-2"   # free again: the next slot
    assert tool(c, "5").returncode == 1
    assert tool(c, "5", "--takeover").stdout.strip() == "claimed claim/5-3"
    monkeypatch.chdir(c)
    assert claim.subject("claim/5-3").startswith("Claim #5 by run-2")
    assert claim.subject("claim/5").startswith("Release #5 by run-0")
    assert sorted(claim.refs(5)) == [1, 2, 3]
    assert sorted(claim.refs(50)) == []                         # claim/5 is no prefix match of claim/50


def test_stale_rule_with_fixed_times():
    """A run that a usage limit stopped at 20:17 (last beat 20:10) is free 30 minutes after its last beat (#231),
    which is before the limit reset (20:30) + 30 minutes. A live run beats again and keeps its ticket."""
    t = lambda hh, mm: (hh * 60 + mm) * 60                                    # noqa: E731
    claim_line, beat = "Claim #9 by run-0 (abc)", t(20, 10)
    assert not claim.stale(claim_line, beat, t(20, 39))
    assert claim.stale(claim_line, beat, t(20, 40))
    assert claim.stale("Beat #9 by run-0", beat, t(21, 0))
    assert not claim.stale("Beat #9 by run-0", t(20, 45), t(21, 0))          # beat after the reset: alive
    assert not claim.stale("Release #9 by run-0", beat, t(23, 0))            # released: free anyway, no takeover


def test_beat_moves_the_claim_time(clones, monkeypatch):
    a, b, _ = clones
    assert tool(a, "6").returncode == 0
    assert tool(b, "6", "--beat").returncode != 0                 # not the claim of run-1
    assert tool(a, "6", "--stale").returncode == 1                # just claimed
    assert tool(a, "6", "--beat").stdout.strip() == "beat claim/6"
    monkeypatch.chdir(a)
    assert claim.subject("claim/6") == "Beat #6 by run-0"
    assert tool(b, "6").returncode == 1                           # a beat is no release
    assert tool(a, "6", "--release").stdout.strip() == "released claim/6"
    assert tool(a, "6", "--stale").returncode == 1                # released: not stale
