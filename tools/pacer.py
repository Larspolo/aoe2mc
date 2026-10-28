"""The pacer as a script (#3193): start the autopilot runs that the quota target misses, with no Claude session.

The pacer session (skill `pacer`) kept an old "cap of 4 per cycle" in its context and fired 4 Haiku runs for H = 8
(2026-10-28, #3147). A script has no memory: `.github/workflows/pacer.yml` runs it every 15 minutes while the
key `pacer` in `[pacing]` of `agent.toml` is "workflow" (one switch for the session and the workflow: a PR changes it).

    python3 tools/pacer.py              # compute K and the lane runs (`usage.fire`), then start them
    python3 tools/pacer.py --dry-run    # print the calls, send nothing

Each scheduled task has an API trigger (a URL and a token, made in the Claude app). The environment gives them:
`PACER_URL_MAIN` and `PACER_TOKEN_MAIN` for the main task, `PACER_URL_<LANE>` and `PACER_TOKEN_<LANE>` for each lane of
`weights` in `[pacing]` of `agent.toml`. A lane without a URL gets no runs: its tickets wait, as with the session.
Exit 1 when a call fails: the workflow run goes red. HTTP 429 is no failure: a task takes at most 30 starts per hour,
an account 100 API starts per hour (the docs of the scheduled tasks, "Usage and limits"); the next cycle starts the
runs that the target still misses. No retry: each call that succeeds starts a run, so a retry can start two. When a
lane task is at its limit, the main task gets the blocked runs, up to the main runs of a new plan without that lane:
the Haiku lane got all 8 runs of each cycle, 48 an hour (2026-10-28).
"""
import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usage  # noqa: E402

MODE = usage.PACER   # "workflow": this script starts the runs
BETA = "experimental-cc-routine-2026-04-01"   # the header of the API trigger of a scheduled task


def calls(k, runs, env):
    """[(task, url, token)]: one call per run. The lane runs go to their lane task, the rest of K to the main task."""
    out = []
    for task, n in [*runs.items(), ("main", k - sum(runs.values()))]:
        url, token = env.get(f"PACER_URL_{task.upper()}"), env.get(f"PACER_TOKEN_{task.upper()}")
        out += [(task, url, token)] * (n if url and token else 0)
    return out


def send(url, token, timeout=30):
    """Start one run of the task of `url`. Raises on an HTTP error."""
    req = urllib.request.Request(url, data=b"{}", method="POST", headers={
        "Authorization": f"Bearer {token}", "anthropic-beta": BETA, "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def main(argv=None, env=os.environ):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="print the calls, send nothing")
    a = ap.parse_args(argv)
    if MODE != "workflow" and not a.dry_run:
        print(f'pacer = "{MODE}" in agent.toml: the pacer session starts the runs, start no run')
        sys.exit(0)
    found, now = usage.read_usage(), datetime.datetime.now(datetime.timezone.utc).timestamp()
    if not found:
        sys.exit("no rate_limit_event in the CLI output: start no run")
    status = usage.read_status()                       # one read for both fire calls (#3069)
    burn, burn7 = usage.burns(status[0])
    k, runs, line = usage.fire(found, now, burn, burn7, status=status)
    todo = calls(k, runs, env)
    skipped = sorted({t for t, n in [*runs.items(), ("main", k - sum(runs.values()))]
                      if n and not env.get(f"PACER_URL_{t.upper()}")})
    failed, limited, started = [], set(), dict.fromkeys([*runs, "main"], 0)
    for task, url, token in todo:
        if a.dry_run:
            print(f"POST {url} ({task})")
        elif task not in limited:
            try:
                send(url, token)
                started[task] += 1
            except urllib.error.HTTPError as e:
                if e.code == 429:                       # the hourly limit: do not call this task again now
                    limited.add(task)
                else:
                    failed.append(f"{task}: HTTP {e.code}")
            except Exception as e:                      # URLError, timeout
                failed.append(f"{task}: {e}")
    blocked = sum(1 for t, *_ in todo if t in limited and t != "main") - sum(started[t] for t in limited)
    if blocked > 0 and "main" not in limited:          # give the room of the blocked lane runs to the main task
        k2, runs2, _ = usage.fire(found, now, burn, burn7, skip=limited, status=status)
        more = calls(min(blocked, k2 - sum(runs2.values())), {}, env)
        for task, url, token in more:
            try:
                send(url, token)
                started[task] += 1
            except urllib.error.HTTPError as e:
                if e.code != 429:
                    failed.append(f"{task}: HTTP {e.code}")
                break
            except Exception as e:
                failed.append(f"{task}: {e}")
                break
    if a.dry_run:
        started = {t: sum(1 for x, *_ in todo if x == t) for t in started}
    print(f"Pacer {datetime.datetime.now(datetime.timezone.utc):%H:%MZ}: K={k}, "
          + ", ".join(f"{t} {n}" for t, n in runs.items())
          + f". {'Would start' if a.dry_run else 'Started'} " + json.dumps(started)
          + (f", no URL for {', '.join(skipped)}" if skipped else "")
          + (f", hourly limit: {', '.join(sorted(limited))}" if limited else "")
          + (f", failed: {'; '.join(failed)}" if failed else "") + f". {line}")
    sys.exit(int(bool(failed)))


if __name__ == "__main__":
    main()
