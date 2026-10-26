"""The quota usage of the Claude subscription, and the number of runs that uses it (owner request, 2026-10-26).

The aim (owner, 2026-10-26): 90 % of the 5-hour window used 2 hours before its reset, then slower to 98 % at the
reset, so that each window reaches the limit (#587).

    python3 tools/usage.py              # five_hour 30% (resets 06:30 UTC, 2.0 h) · seven_day 30% ... · target 12 runs
    python3 tools/usage.py --target     # only the number of runs (rule 4 of the scheduled task)
    python3 tools/usage.py --json
    python3 tools/usage.py --sample     # Usage: <now> · usage 30.0% · resets <time> · claims 9 (for the run report)
    python3 tools/usage.py --fire       # the number of runs that the pacer session starts now (skill `pacer`, #566)

BURN is the default. When the run reports on the status issue have enough `Usage:` lines (at least 5 pairs in the
last 24 hours), `tools/health.py` measures the burn from them and this tool uses that value (#462).

The CLI reports the usage of the subscription in a `rate_limit_event` of its stream-json output. One tiny Haiku
call reads it, about 1 s and a few tokens. All runs share one quota, so each run sees the same numbers.
The pure functions take plain values, so the tests need no network.
"""
import argparse
import datetime
import json
import subprocess
import sys

BURN = 0.03         # share of the 5-hour quota that one run uses per hour (16 runs used about 50 % per hour, 2026-10-25)
MID, MID_LEFT = 0.90, 2.0   # aim: this share is used this many hours before the 5-hour window resets (#587)
END = 0.98          # aim: this share is used when the 5-hour window resets
LO, HI = 1, 16      # bounds of the number of runs
MAX_FIRE = 4        # runs that the pacer starts per cycle: each run needs a few minutes to claim its ticket
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


def target_runs(usage, now, burn=BURN, end=END, lo=LO, hi=HI, mid=MID, mid_left=MID_LEFT):
    """The number of runs that uses `mid` of the 5-hour window `mid_left` hours before its reset, and `end` at the
    reset, with a guard for the 7-day window."""
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
    if "seven_day" in usage:                                    # do not use the week faster than it passes
        used7, reset7, status7 = usage["seven_day"]
        if status7 == "rejected":
            return 0
        elapsed = 1 - max(reset7 - now, 0) / (7 * 86400)
        if used7 > elapsed + 0.10:
            n //= 2
    return max(lo, min(hi, n))


def runs_to_start(target, claims, ready, paused, hi=MAX_FIRE):
    """The number of runs that the pacer starts now: the runs that the target misses, not more than the ready tickets,
    but 1 when no ticket is ready: that run refills the queue (#609).
    Runs that the scheduled task starts cannot start other runs (no `fire_trigger`, #566)."""
    if paused or not target:
        return 0
    return max(0, min(target - claims, max(ready, 1), hi))


def measured_burn():
    """The burn that `tools/health.py` measures from the `Usage:` lines of the status issue, or None."""
    try:
        import health
        return health.measured_burn(health.status_comments(), datetime.datetime.now(datetime.timezone.utc))
    except Exception:                                           # no GitHub access: use the default
        return None


def sample_line(usage, now, claims):
    """The `Usage:` line of a run report, which `tools/health.py` reads."""
    iso = lambda t: f"{datetime.datetime.fromtimestamp(t, datetime.timezone.utc):%Y-%m-%dT%H:%M:%SZ}"
    used, reset, _ = usage["five_hour"]
    return f"Usage: {iso(now)} · usage {used * 100:.1f}% · resets {iso(reset)} · claims {claims}"


def describe(usage, now, burn=BURN):
    out = []
    for k, (used, reset, status) in sorted(usage.items()):
        at = datetime.datetime.fromtimestamp(reset, datetime.timezone.utc)
        out.append(f"{k} {used:.0%} (resets {at:%a %H:%M} UTC, {(reset - now) / 3600:.1f} h, {status})")
    return " · ".join(out) + f" · burn {burn:.3f} · target {target_runs(usage, now, burn)} runs"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", action="store_true", help="print only the number of runs")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sample", action="store_true", help="print the Usage: line for the run report")
    ap.add_argument("--burn", type=float, help="share of the 5-hour quota per run-hour (default: measured, else BURN)")
    ap.add_argument("--fire", action="store_true", help="print the number of runs that the pacer starts now")
    a = ap.parse_args(argv)
    usage, now = read_usage(), datetime.datetime.now(datetime.timezone.utc).timestamp()
    if not usage:
        sys.exit("no rate_limit_event in the CLI output (no subscription, or the CLI changed)")
    if a.sample:
        import health
        print(sample_line(usage, now, health.active_claims(datetime.datetime.now(datetime.timezone.utc))))
        return
    burn = a.burn or measured_burn() or BURN
    if a.fire:
        import dashboard
        import health
        open_all = dashboard.pages("issues?state=open")
        paused = any({"agent-status", "paused"} <= set(dashboard.labels(i)) for i in open_all)
        ready = len(dashboard.candidates(open_all))
        claims = health.active_claims(datetime.datetime.now(datetime.timezone.utc))
        target = target_runs(usage, now, burn)
        print(runs_to_start(target, claims, ready, paused))
        print(f"{describe(usage, now, burn)} · claims {claims} · ready {ready} · paused {paused}", file=sys.stderr)
    elif a.target:
        print(target_runs(usage, now, burn))
    elif a.json:
        print(json.dumps({"usage": usage, "burn": burn, "target": target_runs(usage, now, burn)}))
    else:
        print(describe(usage, now, burn))


if __name__ == "__main__":
    main()
