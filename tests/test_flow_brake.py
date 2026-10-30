"""framework/tools/usage.py: the flow brake lowers the runs when CI or the merges are the bottleneck, not the quota (owner, 2026-10-27)."""
import usage

NOW = 1_800_000_000


def pr(ref, minutes, *labels):
    t = usage.datetime.datetime.fromtimestamp(NOW - minutes * 60, usage.datetime.timezone.utc)
    return {"head": {"ref": ref}, "created_at": f"{t:%Y-%m-%dT%H:%M:%SZ}", "labels": [{"name": n} for n in labels]}


def test_waiting_prs_counts_only_old_agent_prs_without_hold():
    prs = [pr("claude/a", 45), pr("agent/b", 90, "conflict"), pr("claude/c", 5), pr("claude/d", 60, "hold"),
           pr("owner-branch", 120)]
    assert [p["head"]["ref"] for p in usage.waiting_prs(prs, NOW, 30)] == ["claude/a", "agent/b"]


def test_flow_cap():
    assert usage.flow_cap(2, 1, 6, 5)[0] is None                           # no brake: the quota decides
    assert usage.flow_cap(6, 1, 6, 5) == (1, "brake: 6 waiting PRs >= 6, repair only")
    assert usage.flow_cap(9, 5, 6, 5)[0] == 0                              # CI queue: a run cannot help
