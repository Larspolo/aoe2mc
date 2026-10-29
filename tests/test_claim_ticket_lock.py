"""tools/claim.py --ticket KEY: one run makes a new bug ticket (#4231: three copies of one IndexError in 30 seconds)."""
import os
import subprocess
import sys

import claim
from test_claim import clones, tool  # noqa: F401 (fixture)

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "claim.py")
DAY = 86400


def test_one_run_makes_the_bug_ticket(clones):  # noqa: F811
    """Three runs at the same time: one gets the lock. Another spelling of the same symptom is the same lock."""
    procs = [subprocess.Popen([sys.executable, TOOL, "0", "--ticket", "cycle_start IndexError"], cwd=d,
                              stdout=subprocess.PIPE, text=True) for d in clones]
    assert sorted(p.wait() for p in procs) == [0, 1, 1]
    again = tool(clones[1], "0", "--ticket", "cycle_start-indexerror")
    assert again.returncode == 1 and "another run makes the ticket" in again.stdout
    other = tool(clones[2], "0", "--ticket", "pacer timeout")
    assert other.returncode == 0 and other.stdout.strip() == "claimed ticket pacer-timeout"


def test_the_lock_expires_after_a_day():
    now, tips = 1_800_000_000, {"ticket-cycle_start-indexerror": 1_800_000_000 - 2 * DAY,
                                "ticket-pacer-timeout": 1_800_000_000 - 3600}
    assert claim.prunable(tips, open_numbers=set(), now=now) == ["ticket-cycle_start-indexerror"]
