"""The pacer counts a Haiku run as a part of an Opus run (#1727)."""
import datetime
import os
import subprocess
import sys

import health
import usage

T0 = datetime.datetime(2026, 10, 27, 0, tzinfo=datetime.timezone.utc)
RESET = T0 + datetime.timedelta(days=2)
TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "claim.py")


def lines(rows, step=0.25, burn=0.04, weight=0.25):
    """`Usage:` lines every `step` hours. rows: (Opus runs, Haiku runs) at each sample; a Haiku run uses `weight`
    of the quota of an Opus run, and the runs of an interval are the mean of its two samples."""
    used, out, eq = 0.10, [], [o + weight * h for o, h in rows]
    for i, (o, h) in enumerate(rows):
        t = T0 + datetime.timedelta(hours=i * step)
        out.append(usage.sample_line({"five_hour": (used, RESET.timestamp(), "allowed")}, t.timestamp(), o + h,
                                     lanes={"opus": o, "haiku": h}))
        used += burn * step * (eq[i] + eq[min(i + 1, len(eq) - 1)]) / 2
    return [{"body": "\n".join(out)}]


def test_haiku_runs_are_no_plan_upgrade():
    c = lines([(4, 0)] * 89 + [(1, 6)] * 9)                     # 22 h of Opus runs, then 2 h of mostly Haiku runs
    assert abs(health.burn_ratio(health.samples(c, {"haiku": 0.25})) / 0.04 - 1) < 0.01   # no false plan upgrade
    assert health.burn_ratio(health.samples(c, {"haiku": 1.0})) < 0.02   # a Haiku run as a full run: the false upgrade


def test_the_weight_comes_from_the_usage_lines():
    rows = [(4, 0), (2, 4), (3, 2), (1, 6), (4, 1)] * 6
    weights, source = health.lane_weights(lines(rows, weight=0.1))
    assert abs(weights["haiku"] - 0.1) < 0.02 and source["haiku"] == "measured"   # the line rounds to 0.1 %
    weights, source = health.lane_weights(lines([(4, 0), (2, 4)] * 3, weight=0.1))   # too few intervals
    assert weights["haiku"] == 0.25 and source["haiku"] == "start"


def test_the_usage_line_counts_the_lanes():
    line = lines([(1, 2)])[0]["body"].splitlines()[0]
    assert line.endswith("· runs 3 · haiku 2") and health.lane_runs(line) == {"haiku": 2}
    assert health.opus_equivalent(3, {"haiku": 2}, {"haiku": 0.25}) == 1.5


def test_haiku_tickets_get_cheap_runs_first():
    assert usage.lane_plan(2, 0, 3, 3, 0.25, False) == (4, 3)    # 3 Haiku runs (0.75) and 1 Opus run, at most 4
    assert usage.lane_plan(2, 0, 10, 0, 0.25, False) == (2, 0) == (usage.runs_to_start(2, 0, 10, False), 0)
    assert usage.lane_plan(2, 1.75, 10, 3, 0.25, False) == (1, 1)  # 0.25 left: one Haiku run
    assert usage.lane_plan(2, 0, 3, 3, 0.25, True) == (0, 0)


def test_claims_and_beats_carry_the_lane(tmp_path):
    run = lambda *a, cwd: subprocess.run(a, cwd=cwd, capture_output=True, text=True, check=True)
    remote, d = tmp_path / "remote.git", tmp_path / "run"
    run("git", "init", "-q", "--bare", str(remote), cwd=tmp_path)
    run("git", "init", "-q", "-b", "run-0", str(d), cwd=tmp_path)
    run("git", "remote", "add", "origin", str(remote), cwd=d)
    for k, v in (("user.name", "t"), ("user.email", "t@t"), ("aoe2mc.lane", "haiku")):
        run("git", "config", k, v, cwd=d)
    assert subprocess.run([sys.executable, TOOL, "8"], cwd=d, capture_output=True).returncode == 0
    assert run("git", "log", "-1", "--format=%s", "claim/8", cwd=remote).stdout.strip().endswith(" lane haiku")
    assert subprocess.run([sys.executable, TOOL, "8", "--beat"], cwd=d, capture_output=True).returncode == 0
    assert run("git", "log", "-1", "--format=%s", "claim/8", cwd=remote).stdout.strip() == "Beat #8 by run-0 lane haiku"
    now = datetime.datetime.now(datetime.timezone.utc)
    refs = [f"8 {int(now.timestamp())} Beat #8 by run-0 lane haiku", f"9 {int(now.timestamp())} Claim #9 by b (x)"]
    assert health.count_lanes(refs, now) == {"haiku": 1, "opus": 1} and health.count_beating(refs, now) == 2
