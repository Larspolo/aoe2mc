"""Steps 1 to 5 of the `autopilot` skill in one call: it prints only what needs work (owner, 2026-10-28).

The start of a ticket took about 13 tool calls in each run (status issue, usage line, stuck tickets, each open PR, the
CI of main, owner feedback, triage, the pick list), 19 % of the calls of four runs on 2026-10-28. Each call reads the
whole context again. This tool reads all of it and prints one short section per step.

    python3 tools/cycle_start.py                # at the start of a run and before each later ticket
    python3 tools/cycle_start.py --lane haiku   # the pick list of the Haiku lane
    python3 tools/cycle_start.py --last N       # a later ticket of the run: within a priority, the tickets of the
                                                # same epic or files as ticket N first

Sections: `Status` (exit 3 when the status issue has `paused`: stop), `Usage` (keep the line for the report of step 8),
`Stuck` (`claim.py 0 --stuck`), `Flow brake` (`usage.py --flow`), `PRs` (the open agent PRs that need work: red CI,
a conflict, a closed ticket, or green and not merged after 10 minutes), `Main CI` (the last run and the last night run),
`Feedback` (`feedback.py`), `Triage` (open issues without a priority label) and `Candidates` (the pick order of
`dashboard.py --next`, without the tickets that a run holds). The skill says what to do with each line.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dashboard  # noqa: E402
from agent_config import CONFIG  # noqa: E402

TOOLS = os.path.dirname(os.path.abspath(__file__))
AGENT = ("claude/", "agent/")         # the branches of agent PRs (autopilot step 2)
WAITS = {"needs-human", "blocked"}     # a PR of such a ticket waits for the owner or another ticket
STALE, CONFLICT = 30, 10               # minutes without a beat: a stopped run (tools/claim.py STALE, CONFLICT)
SWEEP = 10                             # minutes: a green PR that is still open needs the Automerge sweep (#734)
CLOSE = re.compile(r"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)")
SHOW = 5                               # candidates to print


def tool(*args):
    """(exit code, stdout + stderr) of a tool of this directory."""
    r = subprocess.run([sys.executable, os.path.join(TOOLS, args[0]), *args[1:]], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def beats(lines, now):
    """{ticket: (minutes since the last claim or beat, subject)} of the top claim slots ("<slot> <unix time> <subject>")."""
    top = {}
    for line in lines:
        slot, t, subject = (line.split(" ", 2) + ["", ""])[:3]
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", slot)
        if m and t.isdigit() and (int(m[1]) not in top or int(m[2] or 1) > top[int(m[1])][0]):
            top[int(m[1])] = (int(m[2] or 1), int(t), subject)
    return {n: ((now.timestamp() - t) / 60, s) for n, (_, t, s) in top.items()}


def pr_work(pr, open_issues, checks, beat, now, me=""):
    """The work that an open agent PR needs, or None. pr: an entry of /pulls; checks: [(name, status, conclusion)] of
    its head commit; beat: (minutes, subject) of its ticket claim, or None; me: the current branch. The PRs of this run
    (`<session branch>` and `<session branch>-<k>`, autopilot `more.md`) are yours."""
    if not pr["head"]["ref"].startswith(AGENT) or "hold" in dashboard.labels(pr):
        return None
    m = CLOSE.search(pr.get("body") or "")
    ticket = int(m[1]) if m else None
    issue = open_issues.get(ticket)
    if ticket and issue is None:
        return "its ticket is closed: close the PR when the ticket is \"not planned\""
    if issue and dashboard.labels(issue) & WAITS:
        return None
    conflict = "conflict" in dashboard.labels(pr)
    red = [n for n, s, c in checks if s == "completed" and c in ("failure", "timed_out", "cancelled", "action_required")]
    if not conflict and not red:
        age = (now - dashboard.ts(pr["created_at"])).total_seconds() / 60
        quick = any(n == "quick" and c == "success" for n, _, c in checks)
        return f"green and open {age:.0f} min: start the Automerge sweep (`github.md`)" if quick and age > SWEEP else None
    what = "conflict" if conflict else "red CI: " + ", ".join(red)
    base = re.sub(r"-\d+$", "", me)
    if me and re.fullmatch(re.escape(base) + r"(-\d+)?", pr["head"]["ref"]):
        return f"{what}; a PR of this run: fix it on its branch (`more.md`)"
    live = beat and not beat[1].startswith("Release") and beat[0] < (CONFLICT if conflict else STALE)
    owner = (beat[1].split(" ")[3:4] or ["?"])[0] if beat else None
    if live:
        return f"{what}; its run `{owner}` beat {beat[0]:.0f} min ago: leave it"
    return f"{what}; no live claim: take it over (`overlap.md`), then `merge_main.py --push {ticket}` or fix at step 6.8"


def related(issue, last):
    """True when `issue` has the epic ("Part of #E") or a file or function name of `last`. A later ticket of a run on the
    code that the run already read costs less: 3 trigger tickets in one run cost $1.69 each, 2026-10-28."""
    epics = lambda i: set(re.findall(r"Part of #(\d+)", i.get("body") or ""))
    return bool(epics(issue) & epics(last) or dashboard.names(issue.get("body")) & dashboard.names(last.get("body")))


def prefer(picks, last, lane=None):
    """The pick order with the tickets related to `last` first within each priority (and lane group). The sort is
    stable: the order of `dashboard.candidates` stays inside each group."""
    def group(i):
        prio = next((k for k, p in enumerate(dashboard.PRIORITY) if p in dashboard.labels(i)), len(dashboard.PRIORITY))
        return lane is None and any(n.startswith(dashboard.LANE) for n in dashboard.labels(i)), prio
    return sorted(picks, key=lambda i: (group(i), not related(i, last)))


def main_ci():
    """[(name, conclusion or status, short sha, start time)] of the last CI run on main and of the last night run."""
    out = []
    for name, query in (("last", "branch=main&per_page=1"), ("night", "branch=main&event=schedule&per_page=1")):
        runs = dashboard.api(f"actions/workflows/ci.yml/runs?{query}").get("workflow_runs") or []
        r = runs[0] if runs else {}
        out.append((name, r.get("conclusion") or r.get("status") or "-", (r.get("head_sha") or "-")[:7],
                    (r.get("created_at") or "-")[:16]))
    return out


RED = ("failure", "timed_out", "cancelled")


def merged_fix(log, closed):
    """The first commit of `log` (format `%s%x1f%b%x1e`) that closes a closed "Fix main" ticket or starts with "Fix main"."""
    for rec in log.split("\x1e"):
        subject, _, body = rec.strip().partition("\x1f")
        fixed = [int(n) for n in CLOSE.findall(body) if int(n) in closed]
        if fixed:
            return f"{subject} (#{fixed[0]})"
        if subject.startswith("Fix main"):
            return subject
    return ""


def section(title, lines):
    print(f"{title}: " + ("none" if not lines else lines[0] if len(lines) == 1 else "\n  " + "\n  ".join(lines)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--lane", help="the pick list of this lane (haiku, #1715)")
    ap.add_argument("--last", type=int, help="the last ticket of this run: related tickets first")
    a = ap.parse_args(argv)
    now = datetime.datetime.now(datetime.timezone.utc)
    me = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
    open_all = dashboard.pages("issues?state=open")                  # issues and PRs
    issues = {i["number"]: i for i in open_all if "pull_request" not in i}
    status = next((i for i in issues.values() if dashboard.STATUS in dashboard.labels(i)), None)
    if status is None:
        section("Status", ["no open issue with the label agent-status: make it (`report.md`)"])
    else:
        if CONFIG["status"]["paused"] in dashboard.labels(status):
            section("Status", [f"#{status['number']} has the label paused: stop now, do not comment"])
            return 3
        m = re.search(r"<!-- agent-state: (\{.*?\}) -->", status.get("body") or "")
        state = json.loads(m[1]) if m else {}
        section("Status", [f"#{status['number']} · last run {state.get('last_run', '-')} · runs {state.get('runs', '-')}"])
    code, text = tool("usage.py", "--sample")
    section("Usage (keep it for step 8)", [text.splitlines()[-1] if code == 0 and text else f"- ({text[-200:]})"])
    code, text = tool("claim.py", "0", "--stuck")
    section("Stuck (`overlap.md`, \"Stuck tickets\")", text.splitlines() if code == 0 else [])
    code, text = tool("usage.py", "--flow")
    section("Flow brake", [f"ON: repair one PR or go to step 8, no new ticket ({text})"] if code == 1 else [])
    import health                                                    # health imports dashboard
    held = beats(health.claim_refs() or [], now)
    prs = [p for p in dashboard.pages("pulls?state=open") if p["head"]["ref"].startswith(AGENT)]
    work = []
    for p in prs:
        checks = [(c["name"], c["status"], c["conclusion"]) for c in
                  dashboard.api(f"commits/{p['head']['sha']}/check-runs").get("check_runs", [])]
        m = CLOSE.search(p.get("body") or "")
        w = pr_work(p, issues, checks, held.get(int(m[1])) if m else None, now, me)
        if w:
            work.append(f"PR #{p['number']} (`{p['head']['ref']}`" + (f", #{m[1]}" if m else "") + f"): {w}")
    section(f"PRs ({len(work)} of {len(prs)} open agent PRs need work)", work)
    ci = main_ci()
    fix = [f"#{n} {i['title']}" for n, i in issues.items() if "P0" in dashboard.labels(i) and i["title"].startswith("Fix main")]
    red = [c for c in ci if c[1] in RED]
    done = ""
    if red:
        since = min(t for *_, t in red)
        closed = {i["number"] for i in dashboard.pages(f"issues?state=closed&labels=P0&since={since}:00Z")
                  if i["title"].startswith("Fix main")}
        log = subprocess.run(["git", "log", f"origin/{CONFIG['branch']}", f"--since={since}Z",
                              "--format=%s%x1f%b%x1e"], capture_output=True, text=True).stdout
        done = merged_fix(log, closed)
    section("Main CI", [" · ".join(f"{n} {c} ({sha}, {t})" for n, c, sha, t in ci) + (
        "" if not red else " → red: open P0 tickets \"Fix main\": " + ("; ".join(fix) or "none")
        + (f"; merged after the red run: {done}" if done else ""))])
    code, text = tool("feedback.py")
    section("Feedback (lock each with `claim.py ID --comment`)", [t for t in text.splitlines() if re.match(r"\d+ #\d+ ", t)])
    section("Triage (no priority label)", [f"#{n} {i['title']}" for n, i in sorted(issues.items())
                                           if not dashboard.labels(i) & (set(dashboard.PRIORITY) | {dashboard.STATUS})])
    pr_numbers = [i["number"] for i in open_all if "pull_request" in i]
    busy = dashboard.work(open_all, {n: [f["filename"] for f in dashboard.pages(f"pulls/{n}/files", 3)] for n in pr_numbers})
    hold = {n for n, (m, s) in held.items() if m < STALE and not s.startswith("Release")}
    picks = [i for i in dashboard.candidates(open_all, busy, lane=a.lane) if i["number"] not in hold]
    last = dashboard.api(f"issues/{a.last}") if a.last else None
    if last:
        picks = prefer(picks, last, a.lane)
    section(f"Candidates ({len(picks)} ready, pick order)", [
        f"#{i['number']} {i['title']} ({dashboard.tag(i, 'P')}, {dashboard.tag(i, 'size:')}, overlap "
        f"{len(dashboard.overlap(i, busy))}{', related' if last and related(i, last) else ''})" for i in picks[:SHOW]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
