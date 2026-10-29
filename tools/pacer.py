"""The pacer as a script (#3193): start the autopilot runs that the quota target misses, with no Claude session.

The old pacer session kept an old "cap of 4 per cycle" in its context and fired 4 Haiku runs for H = 8
(2026-10-28, #3147; removed in #3427). A script has no memory: `.github/workflows/pacer.yml` runs it every 10 minutes
while the key `pacer` in `[pacing]` of `agent.toml` is "workflow" (any other value stops the loop: a PR changes it).

    python3 tools/pacer.py              # compute K and the lane runs (`usage.fire`), then start them
    python3 tools/pacer.py --dry-run    # print the calls, send nothing
    python3 tools/pacer.py --log F      # also add the record of the cycle to F, one JSON line (`record`)

Each scheduled task has an API trigger (a URL and a token, made in the Claude app). The environment gives them:
`PACER_URL_MAIN` and `PACER_TOKEN_MAIN` for the main task, `PACER_URL_<LANE>` and `PACER_TOKEN_<LANE>` for each lane of
`weights` in `[pacing]` of `agent.toml`. A lane without a URL gets no runs: its tickets wait.
Exit 1 when a call fails: the workflow run goes red. HTTP 429 is no failure: a task takes at most 30 starts per hour,
an account 100 API starts per hour (the docs of the scheduled tasks, "Usage and limits"); the next cycle starts the
runs that the target still misses. No retry: each call that succeeds starts a run, so a retry can start two. When a
lane task is at its limit, the main task gets the blocked runs, up to the main runs of a new plan without that lane:
the Haiku lane got all 8 runs of each cycle, 48 an hour (2026-10-28).

The pacer also does steps 1 to 5 of the autopilot skill for the runs that it starts (owner, 2026-10-29: the runs
must do as little as possible). For each run it takes the next candidate of its lane in the pick order of
`dashboard.candidates`, claims it for the run (`claim.py` with the name `pacer-r<hex>`: the run has no branch yet),
and sends a brief in the `text` of the call: the ticket, its comments, the code places (`ticket_context.context`) and
the `Usage:` line of the report. The run adopts the claim with its first beat (`claim.py N --adopt NAME`) and starts at
step 6 (the `scheduled` skill). The brief is data in a `<routine-fire-payload>` block: the run takes only its
`ticket` and `claim` lines, and the claim ref in git proves them. A run with no candidate (a refill run), and all runs
while the flow brake is on or the last CI run on main is red, get no brief: they do steps 1 to 5 themselves. When a
call fails, the pacer releases the claim of its run.
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usage  # noqa: E402

BETA = "experimental-cc-routine-2026-04-01"   # the header of the API trigger of a scheduled task


def calls(k, runs, env):
    """[(task, url, token)]: one call per run. The lane runs go to their lane task, the rest of K to the main task."""
    out = []
    for task, n in [*runs.items(), ("main", k - sum(runs.values()))]:
        url, token = env.get(f"PACER_URL_{task.upper()}"), env.get(f"PACER_TOKEN_{task.upper()}")
        out += [(task, url, token)] * (n if url and token else 0)
    return out


HEAD = "aoe2mc pacer brief"     # the first line of a brief: the `scheduled` skill looks for it
TEXT_MAX = 60000                # characters of a brief: the code places are cut first, then the ticket text
RED = ("failure", "timed_out")  # a CI run on main with this result: the runs fix main first (autopilot step 2)
CONTEXT = 120000                # the context up to which a run takes a next ticket (`more.md`: below it a next ticket
CONTEXT_HIGH = 160000           # is cheaper than a fresh run); higher while the task is near its hourly start limit
HOURLY = 30                     # starts per hour of one task (the docs of the scheduled tasks): above 80 % of it a
                                # fresh run may not start, so a run with a large context goes on (#4190)


def context_limit(task, hour):
    """The `context:` line of a brief: the limit of `more.md` for a run of `task`. `hour`: {task: runs} that the pacer
    started in the last 60 minutes (its log, no API call)."""
    return CONTEXT_HIGH if (hour or {}).get(task, 0) >= HOURLY * 0.8 else CONTEXT


def send(url, token, text=None, timeout=30):
    """Start one run of the task of `url`, with `text` as its fire payload. Raises on an HTTP error. Returns the JSON
    answer ({} when it does not parse): `claude_code_session_url` names the new session."""
    req = urllib.request.Request(url, data=json.dumps({"text": text} if text else {}).encode(), method="POST", headers={
        "Authorization": f"Bearer {token}", "anthropic-beta": BETA, "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        try:
            return json.loads(r.read() or b"{}")
        except ValueError:
            return {}


def queues(open_all, refs, now, tasks):
    """{task: [issues]}: the candidates of each task in the pick order of autopilot step 5, without the tickets that
    a run holds (`dashboard.claimed`). The main task takes no ticket of a `reserved` lane (`dashboard.candidates`)."""
    import dashboard
    prs = [i["number"] for i in open_all if "pull_request" in i]
    busy = dashboard.work(open_all, {n: [f["filename"] for f in dashboard.pages(f"pulls/{n}/files", 3)] for n in prs})
    held = dashboard.claimed(refs or [], datetime.datetime.fromtimestamp(now, datetime.timezone.utc))
    return {t: [i for i in dashboard.candidates(open_all, busy, lane=None if t == "main" else t)
                if i["number"] not in held] for t in sorted(set(tasks))}


def brief(issue, comments, name, task, sample, limit=TEXT_MAX, context=CONTEXT):
    """The fire payload of a run: the lines that the run acts on, then the ticket and its code places as data."""
    import claim
    import ticket_context
    head = "\n".join([HEAD, f"ticket: {issue['number']}", f"claim: {name}", f"lane: {task}", f"usage: {sample}",
                      f"context: {context}"])
    text = claim.ticket_text(issue, comments)
    places = ticket_context.context(issue.get("body"))
    out = f"{head}\n\n--- ticket (data) ---\n{text}\n\n--- code places (tools/ticket_context.py) ---\n{places}"
    if len(out) > limit:
        out = out[:limit - 60] + "\n[cut: run `python3 tools/ticket_context.py N` for the rest]"
    return out


def red_main():
    """True when the last CI run on main failed: the runs then do steps 1 to 5, and one of them fixes main."""
    import dashboard
    try:
        runs = dashboard.api("actions/workflows/ci.yml/runs?branch=main&per_page=1").get("workflow_runs") or []
    except Exception:                                   # no answer: give no brief, the runs check it themselves
        return True
    return bool(runs) and runs[0].get("conclusion") in RED


class Briefs:
    """Takes, claims and writes the ticket of each run that the pacer starts (None: no brief for any run)."""

    def __init__(self, todo, out, now, found, dry=False, hour=None):
        self.todo, self.given, self.dry, self.hour = None, [], dry, hour or {}
        if "open" not in out or out.get("flow") is not None or not todo or red_main():
            return
        try:
            self.todo = queues(out["open"], out.get("refs"), now, [t for t, *_ in todo])
        except Exception as e:                          # GitHub failed: the runs pick themselves, as before the briefs
            print(f"no briefs: {e}", file=sys.stderr)
            return
        self.taken, self.sample = set(), usage.sample_line(found, now, out.get("claims") or 0, None, out.get("lanes"))

    def take(self, task):
        """(number, name, text) of the next free ticket of `task`, claimed for its run, or None."""
        import claim
        import dashboard
        for issue in (self.todo or {}).get(task, []):
            n = issue["number"]
            if n in self.taken:
                continue
            self.taken.add(n)
            name = f"pacer-r{uuid.uuid4().hex[:10]}"   # a letter first: `usage.pending` cuts a `-<digits>` end
            if self.dry:
                return n, name, ""
            try:
                if not claim.claim(n, by=name, tag="" if task == "main" else f" lane {task}"):
                    continue                            # a run claimed it after the read
                return n, name, brief(issue, dashboard.pages(f"issues/{n}/comments", 1), name, task, self.sample,
                                         context=context_limit(task, self.hour))
            except (Exception, SystemExit):             # git or GitHub failed (claim.fail exits): the runs claim
                self.todo = None                        # themselves; a claim that stays goes stale in 30 minutes
                self.drop(n, name)
                return None
        return None

    @staticmethod
    def drop(n, name):
        """Release the claim `name` of ticket n, if it was made."""
        import claim
        try:
            claim.release(n, by=name)
        except (Exception, SystemExit):
            pass

    def start(self, task, url, token):
        """Start one run of `task`, with a brief when a ticket is free. Raises like `send`; then the claim goes back."""
        import claim
        got = self.take(task)
        if self.dry:
            print(f"POST {url} ({task})" + (f" #{got[0]}" if got else ""))
            return
        try:
            answer = send(url, token, got[2] if got else None)
        except Exception:
            if got:
                self.drop(got[0], got[1])
            raise
        if got:
            link = answer.get("claude_code_session_url")
            claim.start(got[0], by=got[1], note=f" Session: {link}" if link else "")
            self.given.append(got[0])


NUMBERS = {"target": r"target (\d+) runs", "claims": r"claims (\d+) ", "claims_opus": r"\(([\d.]+) Opus runs\)",
           "ready": r"ready (\d+) ", "refill": r"refill (\d+) "}


def github_limit(env=os.environ, timeout=20):
    """{limit, used, remaining, reset} of the REST calls of the token of the workflows (`/rate_limit` counts no call),
    or None. All workflows of the repository share this hourly limit, and it ran out at 14:22 on 2026-10-29
    ("API rate limit exceeded for installation"): the records show the use per hour and the real limit."""
    if not env.get("GITHUB_TOKEN"):
        return None
    req = urllib.request.Request("https://api.github.com/rate_limit", headers={
        "Authorization": f"Bearer {env['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            core = json.load(r)["resources"]["core"]
    except Exception:                                   # no limit in the record: the starts go on
        return None
    return {k: core.get(k) for k in ("limit", "used", "remaining", "reset")}


def record(at, found, burn, burn7, k, runs, started, line, problems=(), github=None):
    """The JSON record of one cycle (`--log`, 2026-10-29): the quota, the burns, the planned and the started runs, the
    inputs of `usage.fire` and the REST budget of the workflow token (`github_limit`). Only the Actions log had them
    (no tool reads it, and it expires): with the starts and the `Run:` lines of the reports, a run that ends with no
    report shows."""
    rec = {"at": f"{at:%Y-%m-%dT%H:%M:%SZ}", "k": k, "plan": runs, "started": started, "burn": burn, "burn7": burn7,
           "github": github,
           **{w: list(found[w]) for w in ("five_hour", "seven_day") if w in found}}
    for key, rx in NUMBERS.items():
        m = re.search(rx, line)
        rec[key] = None if m is None else float(m[1]) if "." in m[1] else int(m[1])
    return {**rec, "problems": list(problems), "line": line}


def recent_starts(path, now, minutes=usage.PENDING):
    """{task: runs} that the cycles of the log file `path` (`--log`) started in the last `minutes` before `now` (a Unix
    time): `usage.fire` counts those with no claim yet. An absent or broken log: none."""
    out = {}
    try:
        with open(path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    at = datetime.datetime.strptime(r["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
                except (ValueError, KeyError, TypeError):
                    continue
                if at.timestamp() >= now - minutes * 60:
                    for task, n in (r.get("started") or {}).items():
                        out[task] = out.get(task, 0) + n
    except OSError:
        pass
    return out


def main(argv=None, env=os.environ):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="print the calls, send nothing")
    ap.add_argument("--log", metavar="FILE", help="add the record of this cycle to FILE (one JSON line)")
    a = ap.parse_args(argv)
    found, now = usage.read_usage(), datetime.datetime.now(datetime.timezone.utc).timestamp()
    if not found:
        sys.exit("no rate_limit_event in the CLI output: start no run")
    status = usage.read_status()                       # one read for both fire calls (#3069)
    burn, burn7 = usage.burns(status[0])
    started = recent_starts(a.log, now) if a.log else {}   # the runs of the last cycles that have no claim yet
    out = {}
    k, runs, line = usage.fire(found, now, burn, burn7, status=status, started=started, out=out)
    todo = calls(k, runs, env)
    hour = recent_starts(a.log, now, 60) if a.log else {}   # the starts of the last hour: the `context:` line
    briefs = Briefs(todo, out, now, found, a.dry_run, hour)
    skipped = sorted({t for t, n in [*runs.items(), ("main", k - sum(runs.values()))]
                      if n and not env.get(f"PACER_URL_{t.upper()}")})
    failed, limited, started = [], set(), dict.fromkeys([*runs, "main"], 0)
    for task, url, token in todo:
        if a.dry_run:
            briefs.start(task, url, token)
        elif task not in limited:
            try:
                briefs.start(task, url, token)
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
        k2, runs2, _ = usage.fire(found, now, burn, burn7, skip=limited, status=status, started=started)
        more = calls(min(blocked, k2 - sum(runs2.values())), {}, env)
        for task, url, token in more:
            try:
                briefs.start(task, url, token)
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
    at, gh = datetime.datetime.now(datetime.timezone.utc), github_limit(env)
    print(f"Pacer {at:%H:%MZ}: K={k}, "
          + ", ".join(f"{t} {n}" for t, n in runs.items())
          + f". {'Would start' if a.dry_run else 'Started'} " + json.dumps(started)
          + (f", no URL for {', '.join(skipped)}" if skipped else "")
          + (f", hourly limit: {', '.join(sorted(limited))}" if limited else "")
          + (f", failed: {'; '.join(failed)}" if failed else "")
          + (f", briefs {' '.join(f'#{n}' for n in briefs.given)}" if briefs.given else "") + f". {line}"
          + (f" · GitHub API {gh['used']}/{gh['limit']} (reset {gh['reset']})" if gh else ""))
    if a.log and not a.dry_run:
        problems = [f"no URL: {t}" for t in skipped] + [f"hourly limit: {t}" for t in sorted(limited)] + failed
        try:                                            # the log never stops the starts
            with open(a.log, "a") as f:
                f.write(json.dumps({**record(at, found, burn, burn7, k, runs, started, line, problems, gh),
                                    "briefs": briefs.given}) + "\n")
        except OSError as e:
            print(f"no pacer log: {e}", file=sys.stderr)
    sys.exit(int(bool(failed)))


if __name__ == "__main__":
    main()
