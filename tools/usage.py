"""The quota usage of the Claude subscription, and the number of runs that uses it evenly (owner request, 2026-10-26).

    python3 tools/usage.py              # five_hour 30% (resets 06:30 UTC, 2.0 h) · seven_day 30% ... · target 12 runs
    python3 tools/usage.py --target     # only the number of runs (rule 4 of the scheduled task)
    python3 tools/usage.py --json

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
END = 0.95          # aim: this share is used when the 5-hour window resets
LO, HI = 1, 16      # bounds of the number of runs
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


def target_runs(usage, now, burn=BURN, end=END, lo=LO, hi=HI):
    """The number of runs that ends the 5-hour window at `end` used, with a guard for the 7-day window."""
    if not usage or "five_hour" not in usage:
        return None
    used, reset, status = usage["five_hour"]
    if status == "rejected":
        return 0
    hours = max((reset - now) / 3600, 0.25)                     # the last quarter hour: use what is left
    n = round(max(end - used, 0) / hours / burn)
    if "seven_day" in usage:                                    # do not use the week faster than it passes
        used7, reset7, status7 = usage["seven_day"]
        if status7 == "rejected":
            return 0
        elapsed = 1 - max(reset7 - now, 0) / (7 * 86400)
        if used7 > elapsed + 0.10:
            n //= 2
    return max(lo, min(hi, n))


def describe(usage, now):
    out = []
    for k, (used, reset, status) in sorted(usage.items()):
        at = datetime.datetime.fromtimestamp(reset, datetime.timezone.utc)
        out.append(f"{k} {used:.0%} (resets {at:%a %H:%M} UTC, {(reset - now) / 3600:.1f} h, {status})")
    return " · ".join(out) + f" · target {target_runs(usage, now)} runs"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", action="store_true", help="print only the number of runs")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    usage, now = read_usage(), datetime.datetime.now(datetime.timezone.utc).timestamp()
    if not usage:
        sys.exit("no rate_limit_event in the CLI output (no subscription, or the CLI changed)")
    if a.target:
        print(target_runs(usage, now))
    elif a.json:
        print(json.dumps({"usage": usage, "target": target_runs(usage, now)}))
    else:
        print(describe(usage, now))


if __name__ == "__main__":
    main()
