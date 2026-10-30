"""framework/tools/claim.py --refill: one run makes the new tickets of an epic or of the queue refill (#505)."""
import os
import subprocess
import sys

import claim
from test_claim import clones, tool  # noqa: F401 (fixture)

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "claim.py")


def deep(dirs):
    """The lock tests run as deep runs: agent.toml gives these locks only to the deep lane (2026-10-28)."""
    for d in dirs:
        subprocess.run(["git", "config", "aoe2mc.lane", "deep"], cwd=d, check=True)


def test_one_run_refills_an_epic(clones):  # noqa: F811
    """Three runs at the same time: one gets the lock. A later state of the epic gives a new lock."""
    deep(clones)
    procs = [subprocess.Popen([sys.executable, TOOL, "186", "--refill", "--state", "4"], cwd=d,
                              stdout=subprocess.PIPE, text=True) for d in clones]
    assert sorted(p.wait() for p in procs) == [0, 1, 1]
    assert tool(clones[1], "186", "--refill", "--state", "4").returncode == 1
    assert tool(clones[1], "186", "--refill", "--state", "5").stdout.strip() == "claimed refill 186-5"
    assert tool(clones[2], "187", "--refill", "--state", "4").returncode == 0           # another epic
    assert sorted(claim.refs(186, str(clones[0] / ".." / "remote.git"))) == []           # no ticket claim


def test_whole_refill_locks_one_hour(clones):  # noqa: F811
    """Epic 0 (the whole refill) without --state locks the UTC hour and its quarter of a local remote (#609)."""
    deep(clones)
    assert claim.refill_state(0, now=1793000000) == "20261026073"                 # 07:33 UTC: slot 3 of the hour
    assert tool(clones[0], "0", "--refill").returncode == 0
    assert tool(clones[1], "0", "--refill").returncode == 1
