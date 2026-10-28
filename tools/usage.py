"""The quota usage of the Claude subscription, and the number of runs that uses it (owner request, 2026-10-26).

The aim (owner, 2026-10-26): 90 % of the 5-hour window used 2 hours before its reset, then slower to 98 % at the
reset, so that each window reaches the limit (#587).

    python3 tools/usage.py              # five_hour 30% (resets 06:30 UTC, 2.0 h) · seven_day 30% ... · target 12 runs
    python3 tools/usage.py --target     # only the number of runs (rule 4 of the scheduled task)
    python3 tools/usage.py --json
    python3 tools/usage.py --sample     # Usage: <now> · usage 30.0% · resets <time> · runs 9 · week 56.0% · release 61.2%
    python3 tools/usage.py --fire       # the number of runs that the pacer session starts now (skill `pacer`, #566)
    python3 tools/usage.py --flow       # exit 1 when the flow brake is on: the runs repair PRs, no new ticket

The flow brake (owner, 2026-10-27): the quota is not the only bottleneck. When CI, merge conflicts or anything else
stops the merges, the agent PRs build up, and a night of new PRs gives many conflicts. So `--fire` counts the open
agent PRs older than `pr_minutes` (they wait for something that is not the quota) and the queued CI runs. At
`max_waiting_prs` it starts at most 1 run per cycle, and that run only repairs PRs (autopilot step 2). At
`max_ci_queue` it starts no run: a run cannot make CI faster. The limits are in `[pacing]` of `agent.toml`.

BURN and BURN7 (the same for the 7-day window, #1695) are the defaults. When the run reports on the status issue
have enough `Usage:` lines (at least 5 pairs in the last 24 hours), `tools/health.py` measures the burns from them
and this tool uses those values (#462).

The CLI reports the usage of the subscription in a `rate_limit_event` of its stream-json output. One tiny Haiku
call reads it, about 1 s and a few tokens. All runs share one quota, so each run sees the same numbers.
The pure functions take plain values, so the tests need no network.
"""
import argparse
import datetime
import json
import math
import subprocess
import sys

from agent_config import CONFIG

BURN = 0.03         # share of the 5-hour quota that one run uses per hour (16 runs used about 50 % per hour, 2026-10-25)
BURN7 = 0.005       # share of the 7-day quota that one run uses per hour (0.0053 measured on 2026-10-27, #1695)
MID, MID_LEFT = 0.90, 2.0   # aim: this share is used this many hours before the 5-hour window resets (#587)
END = 0.98          # aim: this share is used when the 5-hour window resets
LO, HI = 1, CONFIG.get("pacing", {}).get("max_runs", 16)   # bounds of the number of runs (`agent.toml`, #1706)
FREE7 = CONFIG.get("pacing", {}).get("week_free", 0.60)   # below this 7-day usage only the 5-hour window counts (owner, 2026-10-27)
WEEK_GUARD = CONFIG.get("pacing", {}).get("week_guard", True)   # false: the 7-day usage does not count (owner, 2026-10-28)
WAIT = CONFIG.get("pacing", {}).get("max_waiting_prs", 10)   # flow brake: open agent PRs older than PR_MINUTES
QUEUE = CONFIG.get("pacing", {}).get("max_ci_queue", 5)      # flow brake: queued CI runs (no runner yet)
PR_MINUTES = CONFIG.get("pacing", {}).get("pr_minutes", 30)  # Automerge merges a green PR in a few minutes
MAX_FIRE = CONFIG.get("pacing", {}).get("max_fire", 8)   # runs that the pacer starts per cycle: each run needs a few minutes to claim its ticket; the same as agent.toml (the pacer used an old 4, 2026-10-28)
REFILL = CONFIG.get("pacing", {}).get("refill_runs", 1)   # runs beyond the ready tickets: each refills one epic (#609, #650)
CALL = ["claude", "-p", "Reply with OK.", "--model", "claude-haiku-5-5", "--output-format", "stream-json", "--verbose"]


def parse(lines):
    """{window: (utilization 0..1, resets_at epoch s, status)} from the stream-json lines of the CLI, or {}."""
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "rate_limit_event":
            w = (d.get("rate_limit_info") or {}).get("unifiedWindows") or {}
            return {k: (float(v.get("utilization") or 0), int(v.get("resetsAt") or 0), v.get("status", "")) for k, v in w.items()}
    return {}


def read_usage(timeout=120):
    r = subprocess.run(CALL, capture_output=True, text=True, timeout=timeout, cwd="/tmp")
    return parse(r.stdout.splitlines())


def target_runs(usage, now, burn=BURN, end=END, lo=LO, hi=HI, mid=MID, mid_left=MID_LEFT, burn7=None, free7=FREE7,
                week=WEEK_GUARD):
    """The number of runs that uses `mid` of the 5-hour window `mid_left` hours before its reset, and `end` at the
    reset, with a guard for the 7-day window. burn7 (the share of the 7-day quota of one run-hour, measured): a week
    used ahead of the time gets at most the runs that its budget (1 - used) carries to the 7-day reset (#1695). This
    count can be 0, below `lo`: the week has no budget for a run now, and the budget per hour grows while the reset
    comes nearer. Without burn7 the count of a week ahead by more than 10 points is half. Below `free7` of the 7-day
    usage there is no guard: the runs hit the 5-hour limit, not the weekly pace (owner, 2026-10-27). With `week` false
    (`week_guard` of `agent.toml`) there is no guard at all (owner, 2026-10-28)."""
    if not usage or "five_hour" not in usage:
        return None
    used, reset, status = usage["five_hour"]
    if status == "rejected":
        return 0
    left = (reset - now) / 3600
    if left > mid_left and used < mid:                          # the first 3 hours: fast to `mid`
        aim, hours = mid, left - mid_left
    else:                                                       # the last 2 hours: slow to `end`
        aim, hours = end, left
    hours = max(hours, 0.25)                                    # the last quarter hour: use what is left
    n = round(max(aim - used, 0) / hours / burn)
    if week and "seven_day" in usage:                           # do not use the week faster than it passes
        used7, reset7, status7 = usage["seven_day"]
        if status7 == "rejected":
            return 0
        if used7 < free7:
            return max(lo, min(hi, n))
        elapsed = 1 - max(reset7 - now, 0) / (7 * 86400)
        if burn7 and used7 > elapsed:
            fit = max(1 - used7, 0) / max((reset7 - now) / 3600, 0.25) / burn7
            return min(max(lo, min(hi, n)), math.floor(fit))
        if used7 > elapsed + 0.10:
            n //= 2
    return max(lo, min(hi, n))


def week_line(usage, now):
    """The 7-day projection: the points ahead of the time, and when the quota runs out at the mean rate of the week
    so far (or that it lasts to the reset), for example `week ahead +38 pt · runs out Wed 10:00`. "" without it."""
    if "seven_day" not in usage:
        return ""
    used7, reset7, _ = usage["seven_day"]
    gone = 7 * 86400 - max(reset7 - now, 0)
    line = f"week ahead {(used7 - gone / (7 * 86400)) * 100:+.0f} pt"
    if used7 <= 0 or gone <= 0:
        return line
    out = now + (1 - used7) / (used7 / gone)
    at = datetime.datetime.fromtimestamp(out, datetime.timezone.utc)
    return line + (f" · runs out {at:%a %H:%M}" if out < reset7 else " · lasts to the reset")


def runs_to_start(target, claims, ready, paused, hi=MAX_FIRE, refill=REFILL):
    """The number of runs that the pacer starts now: the runs that the target misses, not more than the ready tickets
    and `refill` more: these refill the queue, one epic each, then take a new ticket (#609). One refill run left the
    queue at 3 ready tickets for 40 target runs (2026-10-28).
    Runs that the scheduled task starts cannot start other runs (no `fire_trigger`, #566)."""
    if paused or not target:
        return 0
    return max(0, min(target - claims, ready + refill, hi))


def refill_runs(issues, now, minutes=60, refill=REFILL):
    """`refill` when an open ticket is newer than `minutes` (the refills still find work), else 1: when the epics have
    no goal left, the refill runs find nothing and stop, and one run is enough to start the next epic (`roadmap`).
    issues: the open issues and PRs; now: Unix seconds."""
    new = any("pull_request" not in i and now - datetime.datetime.fromisoformat(
        i["created_at"].replace("Z", "+00:00")).timestamp() < minutes * 60 for i in issues)
    return refill if new else min(refill, 1)


def plan(target, claims, ready, lanes, paused, hi=MAX_FIRE, refill=REFILL, refill_lane=None):
    """(K, {lane: runs}): the runs that the pacer starts now and the runs of each lane among them (#1715, #1727).
    lanes: [(name, ready tickets of the lane, weight)] in the order of their start. The target and the claims are in Opus
    runs, and a lane run counts its weight. Each lane gets runs for its ready tickets while the room lasts;
    `refill_lane` (the deep lane, 2026-10-28) also gets the `refill` runs: the queue refill is its work. The Opus runs
    take the rest of the target: at most the other ready tickets, and the `refill` runs when no lane refills (#609).
    A lane run that counts more than one Opus run (deep: 4) starts also when the room holds only one: else the main
    runs fill each small room first, and its tickets wait for ever. Its claim then counts its weight."""
    if paused or not target:
        return 0, {name: 0 for name, *_ in lanes}
    room, left, rest, out = target - claims, hi, ready, {}
    for name, n, w in lanes:
        want = n + (refill if name == refill_lane else 0)
        fit = math.floor(room / w + 1e-9) or int(room >= 1)
        k = max(0, min(want, left, fit)) if room > 0 else 0
        out[name], room, left, rest = k, room - k * w, left - k, rest - min(k, n)
    o = max(0, min(math.floor(room + 1e-9), rest + (0 if refill_lane else refill), left))
    return o + sum(out.values()), out


def lane_plan(target, claims, ready, ready_haiku, weight, paused, hi=MAX_FIRE, refill=REFILL):
    """(K, H): `plan` with the Haiku lane alone."""
    k, lanes = plan(target, claims, ready, [("haiku", ready_haiku, weight)], paused, hi, refill)
    return k, lanes["haiku"]


def waiting_prs(prs, now, minutes=PR_MINUTES):
    """The open agent PRs (branch `claude/*` or `agent/*`) older than `minutes`, without `hold` (the owner holds
    those): each waits for a fix, a conflict merge or CI, not for the quota."""
    old = now - minutes * 60
    return [p for p in prs if p["head"]["ref"].startswith(("claude/", "agent/"))
            and "hold" not in {x["name"] for x in p.get("labels", [])}
            and datetime.datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")).timestamp() < old]


def flow_cap(waiting, queued, max_waiting=WAIT, max_queue=QUEUE):
    """(cap, reason): the most runs that the pacer starts now when the flow is the bottleneck, not the quota.
    cap None: no brake. Too many queued CI runs: 0 (a run cannot make CI faster). Too many waiting PRs: 1, a run that
    only repairs PRs (autopilot step 2), so that the open PRs go down before new PRs come."""
    if queued >= max_queue:
        return 0, f"brake: CI queue {queued} >= {max_queue}"
    if waiting >= max_waiting:
        return 1, f"brake: {waiting} waiting PRs >= {max_waiting}, repair only"
    return None, f"flow ok: {waiting} waiting PRs, CI queue {queued}"


def read_flow(now):
    """(cap, reason) from GitHub: the open PRs and the queued workflow runs."""
    import dashboard
    prs = dashboard.pages("pulls?state=open")
    queued = dashboard.api("actions/runs?status=queued&per_page=1")["total_count"]
    return flow_cap(len(waiting_prs(prs, now)), queued)


def measured_burn7():
    """The share of the 7-day quota of one run-hour that `tools/health.py` measures from the `Usage:` lines, or None."""
    try:
        import health
        return health.weekly_burn(health.status_comments(), datetime.datetime.now(datetime.timezone.utc))
    except Exception:                                           # no GitHub access: the old guard
        return None


def measured_burn():
    """The burn that `tools/health.py` measures from the `Usage:` lines of the status issue, or None."""
    try:
        import health
        return health.measured_burn(health.status_comments(), datetime.datetime.now(datetime.timezone.utc))
    except Exception:                                           # no GitHub access: use the default
        return None


def sample_line(usage, now, claims, release=None, lanes=None):
    """The `Usage:` line of a run report, which `tools/health.py` reads: also the 7-day usage and the release percent
    of all goals (tools/release.py), for the release progress per quota (#899)."""
    iso = lambda t: f"{datetime.datetime.fromtimestamp(t, datetime.timezone.utc):%Y-%m-%dT%H:%M:%SZ}"
    used, reset, _ = usage["five_hour"]
    line = f"Usage: {iso(now)} · usage {used * 100:.1f}% · resets {iso(reset)} · runs {claims}"
    if "seven_day" in usage:
        line += f" · week {usage['seven_day'][0] * 100:.1f}%" + ("" if release is None else f" · release {release:.1f}%")
        line += f" · week resets {iso(usage['seven_day'][1])}"                  # for the dashboard (#1696)
    return line + "".join(f" · {k} {n}" for k, n in sorted((lanes or {}).items()) if k != "opus" and n)   # (#1727)


def release_percent():
    """The percent of milestone C over all goals (tools/release.py), or None without GitHub access."""
    try:
        import release
        return release.total(release.current())
    except Exception:
        return None


def describe(usage, now, burn=BURN, burn7=None):
    out = []
    for k, (used, reset, status) in sorted(usage.items()):
        at = datetime.datetime.fromtimestamp(reset, datetime.timezone.utc)
        out.append(f"{k} {used:.0%} (resets {at:%a %H:%M} UTC, {(reset - now) / 3600:.1f} h, {status})")
    week = week_line(usage, now) + (f" · burn7 {burn7:.4f}" if burn7 else "")
    return " · ".join(out + [week] * bool(week)) + f" · burn {burn:.3f} · max {HI} runs · target {target_runs(usage, now, burn, burn7=burn7)} runs"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", action="store_true", help="print only the number of runs")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sample", action="store_true", help="print the Usage: line for the run report")
    ap.add_argument("--burn", type=float, help="share of the 5-hour quota per run-hour (default: measured, else BURN)")
    ap.add_argument("--fire", action="store_true", help="print the number of runs that the pacer starts now")
    ap.add_argument("--flow", action="store_true", help="exit 1 when the flow brake is on (repair PRs, no new ticket)")
    a = ap.parse_args(argv)
    if a.flow:                                                  # no quota call: autopilot step 2 asks only this
        cap, reason = read_flow(datetime.datetime.now(datetime.timezone.utc).timestamp())
        print(reason)
        sys.exit(int(cap is not None))
    usage, now = read_usage(), datetime.datetime.now(datetime.timezone.utc).timestamp()
    if not usage:
        sys.exit("no rate_limit_event in the CLI output (no subscription, or the CLI changed)")
    if a.sample:
        import health
        t = datetime.datetime.now(datetime.timezone.utc)
        print(sample_line(usage, now, health.active_claims(t), release_percent(), health.lane_claims(t)))
        return
    burn, burn7 = a.burn or measured_burn() or BURN, measured_burn7() or BURN7
    if a.fire:
        import dashboard
        import health
        open_all = dashboard.pages("issues?state=open")
        paused = any({dashboard.STATUS, dashboard.PAUSED} <= set(dashboard.labels(i)) for i in open_all)
        ready = len(dashboard.candidates(open_all, reserved=()))   # all lanes: lane_plan splits them
        t = datetime.datetime.now(datetime.timezone.utc)
        lanes = health.lane_claims(t)
        claims = health.active_claims(t) if lanes is None else sum(lanes.values())
        weights, source = health.lane_weights(health.status_comments())
        eq = claims if lanes is None else health.opus_equivalent(claims, lanes, weights)   # in Opus runs (#1727)
        target = target_runs(usage, now, burn, burn7=burn7)
        refill = refill_runs(open_all, now)
        lanes = [(n, len(dashboard.candidates(open_all, lane=n)), weights[n]) for n in weights]   # agent.toml order
        k, runs = plan(target, eq, ready, lanes, paused, refill=refill,
                       refill_lane="deep" if "deep" in dashboard.RESERVED else None)
        cap, flow = read_flow(now)
        if cap is not None:                                     # the flow is the bottleneck: Opus runs repair the PRs
            k, runs = min(k, cap), dict.fromkeys(runs, 0)
        print(k)
        for n, r in runs.items():
            print(f"{n} {r}")
        print(f"{describe(usage, now, burn, burn7)} · claims {claims} ({eq:.2f} Opus runs) · ready {ready} · refill {refill} · "
              f"paused {paused} · {flow} · max_fire {MAX_FIRE} · weights " + ", ".join(f"{n} {w:.2f} ({source[n]})" for n, w in weights.items()),
              file=sys.stderr)
    elif a.target:
        print(target_runs(usage, now, burn, burn7=burn7))
    elif a.json:
        print(json.dumps({"usage": usage, "burn": burn, "burn7": burn7, "target": target_runs(usage, now, burn, burn7=burn7)}))
    else:
        print(describe(usage, now, burn, burn7))


if __name__ == "__main__":
    main()
