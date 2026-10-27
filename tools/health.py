"""Numbers of the whole system for the `improve` skill: CI, environment, repository and scheduling (#242).

    python3 tools/health.py              # the last 24 hours
    python3 tools/health.py --hours 72
    python3 tools/health.py --hours 24 --until 2026-10-26T05:15:00Z   # the 24 hours before a time (#489)

REST only (cloud sessions give 403 for GraphQL and `search/...`). Token and `gh` fallback as in
`tools/dashboard.py`. The parsing functions take plain JSON, so the tests need no network.
"""
import argparse
import datetime
import os
import re
import statistics
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent_config import CONFIG  # noqa: E402
from dashboard import api, closes  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CI_JOB_RUNS = 20                          # read the step times of this many CI runs (one API call each)
DENY = (".log", ".mca", ".png")           # suffixes that do not belong in git ...
DENY_OK = ("docs/", "samples/")           # ... except .png in these folders
BIG = 1 << 20
OWNER = CONFIG["owner"]                   # a reopen by the owner is rework (#899)
STATUS = CONFIG["status"]["label"]


def ts(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def minutes(a, b):
    return (ts(b) - ts(a)).total_seconds() / 60


def med(xs):
    return statistics.median(xs) if xs else None


def ci_runs(runs, since):
    """{workflow: (count, median min, max min, failures)} of the completed runs that started after `since`."""
    by = {}
    for r in runs:
        if r.get("status") == "completed" and ts(r["run_started_at"]) >= since:
            by.setdefault(r["name"], []).append(r)
    out = {}
    for name, rs in sorted(by.items()):
        m = [minutes(r["run_started_at"], r["updated_at"]) for r in rs]
        out[name] = (len(rs), med(m), max(m), sum(r["conclusion"] == "failure" for r in rs))
    return out


def slow_steps(jobs, n=3):
    """[(median min, "job / step")] of the n slowest steps over all jobs (the `jobs` lists of several runs)."""
    times = {}
    for job in jobs:
        for s in job.get("steps", []):
            if s.get("started_at") and s.get("completed_at"):
                times.setdefault(f"{job['name']} / {s['name']}", []).append(
                    minutes(s["started_at"], s["completed_at"]))
    return sorted(((med(v), k) for k, v in times.items()), reverse=True)[:n]


def setup_minutes(comments):
    """The `setup <m> min` values of the `Metrics:` lines."""
    return [float(m) for c in comments for line in (c.get("body") or "").splitlines() if line.startswith("Metrics:")
            for m in re.findall(r"setup (\d+(?:\.\d+)?) min", line)]


def events(comments):
    """Counts of takeovers, releases and merge conflicts in the issue and PR comments. A conflict counts only from
    the comments of the workflows: Automerge could not merge, or Unconflict solved it alone ("solved"). Run reports
    that only name a conflict counted 5 times too many (improve, run 145)."""
    bodies = [(c.get("body") or "").lstrip() for c in comments]
    return {"takeovers": sum(b.startswith("Taken over by") for b in bodies),
            "releases": sum(b.startswith("Released") for b in bodies),
            "conflicts": sum(b.startswith("CI is green, but the merge failed") for b in bodies),
            "solved": sum(b.startswith("Merged `main` into the branch") for b in bodies)}


def claim_to_merge(prs, comments, since):
    """Minutes from the last "Started by" comment on the ticket to the merge, for PRs merged after `since`."""
    started = {}
    for c in comments:
        if (c.get("body") or "").startswith("Started by"):
            n = int(c["issue_url"].rsplit("/", 1)[1])
            started.setdefault(n, []).append(c["created_at"])
    out = []
    for pr in prs:
        if pr.get("merged_at") and ts(pr["merged_at"]) >= since:
            for n in closes(pr):
                before = [t for t in started.get(n, []) if t <= pr["merged_at"]]
                if before:
                    out.append(minutes(max(before), pr["merged_at"]))
    return out


def bad_files(files):
    """[(path, bytes)] of the files over 1 MB or with a denied suffix. files: [(path, bytes)]."""
    return [(p, size) for p, size in files if size > BIG
            or (p.endswith(DENY) and not (p.endswith(".png") and p.startswith(DENY_OK)))]


# `runs N` since #635 (claim beats); the older `claims N` lines counted too few runs, so they do not count.
SAMPLE = re.compile(r"^Usage: (\S+) · usage (\d+(?:\.\d+)?)% · resets (\S+) · runs (\d+)", re.M)


def samples(comments):
    """[(time, 5-hour usage 0..1, reset time, claims)] of the `Usage:` lines of the run reports (#462), by time."""
    return sorted((ts(t), float(u) / 100, ts(r), int(k)) for c in comments
                  for t, u, r, k in SAMPLE.findall(c.get("body") or ""))


def burn_pairs(samples, min_hours=0.25):
    """Share of the 5-hour quota that one run uses per hour, from each sample and the first later sample in the same
    window (the same reset time) at least `min_hours` later: the rise of the usage divided by the hours and the mean
    number of claims. Runs report a few minutes apart, so neighbours alone give almost no pairs (#571)."""
    out = []
    for i, a in enumerate(samples):
        b = next((b for b in samples[i + 1:] if abs((b[2] - a[2]).total_seconds()) < 600
                  and (b[0] - a[0]).total_seconds() >= min_hours * 3600), None)
        if b and b[1] >= a[1] and a[3] + b[3] > 0:
            out.append((b[1] - a[1]) / ((b[0] - a[0]).total_seconds() / 3600) / ((a[3] + b[3]) / 2))
    return out


def burn_ratio(samples, need=5):
    """Share of the 5-hour quota that one run uses per hour: the sum of the usage rises divided by the sum of the
    claim-hours (hours x mean claims) of consecutive samples in the same window, or None with fewer than `need` such
    intervals. Not a median of pairs: a pair with few claims gives a large value, because the runs between tickets
    and the other sessions also use the quota (0.111 against 0.059 on 2026-10-26, #582)."""
    out = []
    for a, b in zip(samples, samples[1:]):
        h = (b[0] - a[0]).total_seconds() / 3600
        if abs((b[2] - a[2]).total_seconds()) < 600 and b[1] >= a[1] and h > 0 and a[3] + b[3] > 0:
            out.append((b[0], b[1] - a[1], h * (a[3] + b[3]) / 2))
    return ratio(out, need)


DROP_HOURS = 2      # the period that shows a plan upgrade in the burn (#1706)


def ratio(intervals, need):
    """The sum of the rises divided by the sum of the claim-hours of the intervals [(end, rise, claim-hours)], or None
    with fewer than `need`. When the intervals of the last DROP_HOURS (at least `need`) give less than half of that,
    only they count: after a plan upgrade a run uses a smaller share of the larger quota at once, and the old intervals
    would keep the target too low for a day (#1706)."""
    def of(iv):
        return sum(r for _, r, _ in iv) / sum(c for _, _, c in iv) if len(iv) >= need else None
    whole = of(intervals)
    if whole:
        end = max(t for t, _, _ in intervals) - datetime.timedelta(hours=DROP_HOURS)
        last = of([i for i in intervals if i[0] > end])
        if last and last < whole / 2:
            return last
    return whole


WEEK_RUNS = re.compile(r"^Usage: (\S+) · .*?· runs (\d+) · week (\d+(?:\.\d+)?)%", re.M)


def weekly_burn(comments, now, hours=24, need=5):
    """Share of the 7-day quota that one run uses per hour (#1695): the sum of the rises of the 7-day usage of
    consecutive `Usage:` lines of the last `hours`, divided by their claim-hours, as burn_ratio. A drop is the 7-day
    reset. None with fewer than `need` intervals. A plan upgrade: `ratio`."""
    pts = sorted((ts(t), int(k), float(w) / 100) for c in comments for t, k, w in WEEK_RUNS.findall(c.get("body") or ""))
    pts = [p for p in pts if p[0] >= now - datetime.timedelta(hours=hours)]
    out = [(b[0], b[2] - a[2], (b[0] - a[0]).total_seconds() / 3600 * (a[1] + b[1]) / 2) for a, b in zip(pts, pts[1:])
           if b[2] >= a[2] and b[0] > a[0] and a[1] + b[1] > 0]
    return ratio(out, need) or None


def measured_burn(comments, now, hours=24, need=5):
    """The burn ratio of the samples of the last `hours`, or None when there are fewer than `need` intervals."""
    return burn_ratio([s for s in samples(comments) if s[0] >= now - datetime.timedelta(hours=hours)], need)


PHASES = ("read", "claim", "code", "verify", "ci", "conflict", "report")    # the phase minutes of a Metrics line (#899)
WEEK = re.compile(r"^Usage: (\S+) · .*?· week (\d+(?:\.\d+)?)%(?: · release (\d+(?:\.\d+)?)%)?", re.M)


def phase_minutes(comments):
    """{phase: minutes} summed over the `phases read N · claim N ...` parts of the `Metrics:` lines. Old lines have no
    phases and add nothing."""
    out = dict.fromkeys(PHASES, 0.0)
    for c in comments:
        for line in (c.get("body") or "").splitlines():
            if line.startswith("Metrics:") and " phases " in line:
                for k, v in re.findall(r"\b([a-z]+) (\d+(?:\.\d+)?)\b", line.split(" phases ", 1)[1]):
                    if k in out:
                        out[k] += float(v)
    return out


def quota_per_merge(samples, merged):
    """The rise of the 5-hour usage (0..1) over the samples, summed over consecutive samples in the same window, per
    merged PR; None without merges or rises."""
    rise = sum(b[1] - a[1] for a, b in zip(samples, samples[1:])
               if abs((b[2] - a[2]).total_seconds()) < 600 and b[1] >= a[1])
    return rise / merged if merged and rise else None


TOKENS = re.compile(r"^Tokens: (\d+(?:\.\d+)?)M eq · .*?· sinks (.*)$", re.M)


def token_lines(comments):
    """[(M eq, {sink: share 0..1})] of the `Tokens:` lines of the run reports (tools/tokens.py, owner 2026-10-27)."""
    return [(float(m), {k: float(v) / 100 for k, v in re.findall(r"(\S.*?) (\d+)%(?:, |$)", sinks)})
            for c in comments for m, sinks in TOKENS.findall(c.get("body") or "")]


def token_sinks(lines, k=6):
    """[(sink, share of all eq)] of the k largest sinks over the `Tokens:` lines: the token bottleneck."""
    total, by = sum(m for m, _ in lines), {}
    for m, sinks in lines:
        for s, x in sinks.items():
            by[s] = by.get(s, 0) + m * x
    return sorted(((s, x / total) for s, x in by.items()), key=lambda kv: -kv[1])[:k] if total else []


def weekly(comments):
    """[(time, 7-day usage %, release % or None)] of the `Usage:` lines that have the week (usage.py --sample), by time."""
    return sorted((ts(t), float(w), float(r) if r else None) for c in comments for t, w, r in WEEK.findall(c.get("body") or ""))


def release_per_week(points):
    """(release points per 1 % of 7-day quota, first release %, last release %) from weekly(), or None. The quota is
    the sum of the rises of the 7-day usage (a drop is its reset)."""
    pts = [p for p in points if p[2] is not None]
    used = sum(b[1] - a[1] for a, b in zip(pts, pts[1:]) if b[1] > a[1])
    return ((pts[-1][2] - pts[0][2]) / used, pts[0][2], pts[-1][2]) if len(pts) > 1 and used else None


def weak_spots(issues, events, prs, runs, since):
    """Counts that cost quality: issues that the owner reopened, bug tickets that name a PR merged since `since`
    (rework), bug tickets that name a check ticket ("Check ..."), and failed night runs of CI."""
    new = [i for i in issues if "pull_request" not in i and ts(i["created_at"]) >= since]
    bugs = [i for i in new if "bug" in {lb["name"] for lb in i.get("labels", [])}]
    merged = {p["number"] for p in prs if p.get("merged_at") and ts(p["merged_at"]) >= since}
    checks = {i["number"] for i in issues if i["title"].startswith("Check ")}
    named = lambda i: {int(n) for n in re.findall(r"#(\d+)", i.get("body") or "")}
    return {"reopened": sum(e["event"] == "reopened" and (e.get("actor") or {}).get("login") == OWNER
                            and ts(e["created_at"]) >= since for e in events),
            "rework": sum(bool(named(i) & merged) for i in bugs),
            "check bugs": sum(bool(named(i) & checks) for i in bugs),
            "red nights": sum(r["name"] == "CI" and r.get("event") == "schedule" and r.get("conclusion") == "failure"
                              and ts(r["run_started_at"]) >= since for r in runs)}


def status_comments(hours=24):
    """The comments on the status issue of the last `hours`."""
    status = api(f"issues?state=open&labels={STATUS}")
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    return api_pages(f"issues/{status[0]['number']}/comments?since={since:%Y-%m-%dT%H:%M:%SZ}") if status else []


def count_beating(lines, now, minutes=25):
    """The tickets whose claim ref (top slot `N` or `N-k`) had a claim or beat in the last `minutes` and is not
    released. `lines`: "<slot> <commit time> <subject>" of the refs claim/<slot>."""
    top = {}
    for line in lines:
        slot, t, subject = (line.split(" ", 2) + [""])[:3]
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", slot)
        if m and t.isdigit():
            n, k = int(m.group(1)), int(m.group(2) or 1)
            if n not in top or k > top[n][0]:
                top[n] = (k, int(t), subject)
    cut = now.timestamp() - minutes * 60
    return sum(t >= cut and not s.startswith("Release") for _, t, s in top.values())


def beating_claims(now, minutes=25, remote="origin"):
    """The runs that work now: runs beat at least every 20 minutes, also while they work long on one ticket and the
    issue does not change (#635). None when git cannot read the claim refs."""
    git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT)
    if git("fetch", "-q", "--prune", remote, "+refs/heads/claim/*:refs/aoe2mc-claims/*").returncode:
        return None
    out = git("for-each-ref", "refs/aoe2mc-claims", "--format=%(refname:lstrip=2) %(committerdate:unix) %(subject)")
    return count_beating(out.stdout.splitlines(), now, minutes) if out.returncode == 0 else None


def active_claims(now, minutes=30):
    """The runs that work now (rule 4 of the scheduled task): the claim beats, else the open tickets with
    `in-progress` that changed in the last `minutes`."""
    n = beating_claims(now)
    if n is not None:
        return n
    return sum(ts(i["updated_at"]) >= now - datetime.timedelta(minutes=minutes)
               for i in api("issues?state=open&labels=in-progress&per_page=100") if "pull_request" not in i)


def pr_results(comments, prs):
    """The `pr #n` results of the `Metrics:` lines: (merged PRs, not merged PRs) by the present PR state (#902)."""
    merged = {p["number"] for p in prs if p.get("merged_at")}
    ns = sorted({int(n) for c in comments for line in (c.get("body") or "").splitlines() if line.startswith("Metrics:")
                 for n in re.findall(r"· pr #(\d+) ·", line)})
    return [n for n in ns if n in merged], [n for n in ns if n not in merged]


def fmt(x):
    return "-" if x is None else f"{x:.1f}"


def conflicted(comments):
    """The numbers of the PRs that Automerge could not merge because of a merge conflict (events)."""
    return sorted({int(c["issue_url"].rsplit("/", 1)[1]) for c in comments
                   if (c.get("body") or "").lstrip().startswith("CI is green, but the merge failed")})


def conflict_files(files_of, n=5):
    """The n files that the most conflicted PRs change: where parallel tickets meet (files_of: PR -> file names)."""
    return Counter(f for fs in files_of.values() for f in set(fs)).most_common(n)


def report(since, runs, jobs, status_comments, comments, prs, files, files_of=None, issues=(), issue_events=(),
           unanswered=None):
    out = [f"Health since {since:%Y-%m-%d %H:%M} UTC", "", "CI runs (count, median min, max min, failures):"]
    for name, (k, m, mx, fail) in ci_runs(runs, since).items():
        out.append(f"  {name}: {k}, {fmt(m)}, {fmt(mx)}, {fail}")
    out.append("Slowest CI steps (median min): " + "; ".join(f"{k} {fmt(m)}" for m, k in slow_steps(jobs)))
    setup = setup_minutes(status_comments)
    out.append(f"Setup (median min of {len(setup)} Metrics lines): {fmt(med(setup))}")
    ok, lost = pr_results(status_comments, prs)
    out.append(f"Metrics lines with pr #n: merged {len(ok)}, not merged {len(lost)}"
               + (f" ({', '.join(f'#{n}' for n in lost)})" if lost else ""))
    e = events(comments)
    out.append(f"Takeovers {e['takeovers']}, releases {e['releases']}, merge conflicts {e['conflicts']} (solved by Unconflict {e['solved']})")
    if files_of:
        out.append(f"Files of the {len(files_of)} conflicted PRs (PRs): "
                   + "; ".join(f"{f} {k}" for f, k in conflict_files(files_of)))
    s = [x for x in samples(status_comments) if x[0] >= since]
    b, r = burn_pairs(s), burn_ratio(s)
    out.append(f"Burn per run-hour (ratio of sums of {len(s)} Usage lines, used by usage.py): "
               f"{'-' if r is None else f'{r:.3f}'} · median of {len(b)} pairs: {'-' if not b else f'{med(b):.3f}'}")
    ph = phase_minutes(status_comments)
    total = sum(ph.values())
    out.append("Phases (min, share of the Metrics lines with phases): " + ("; ".join(
        f"{k} {fmt(v)} ({v / total:.0%})" for k, v in ph.items()) if total else "-"))
    merged = sum(1 for p in prs if p.get("merged_at") and ts(p["merged_at"]) >= since)
    q = quota_per_merge(s, merged)
    out.append(f"Quota per merged PR: {'-' if q is None else f'{q:.1%}'} of the 5-hour window ({merged} merged)")
    tl = token_lines(status_comments)
    out.append(f"Tokens per run (median of {len(tl)} Tokens lines): {fmt(med([m for m, _ in tl]))}M eq"
               + (f" · per merged PR {sum(m for m, _ in tl) / len(ok):.2f}M eq" if tl and ok else "")
               + " · largest sinks: " + ("; ".join(f"{s} {x:.0%}" for s, x in token_sinks(tl)) or "-"))
    rw = release_per_week([p for p in weekly(status_comments) if p[0] >= since])
    out.append("Release per 1 % of 7-day quota: " + ("-" if rw is None else
               f"{rw[0]:.2f} points ({rw[1]:g} % to {rw[2]:g} %)"))
    w = weak_spots(issues, issue_events, prs, runs, since)
    out.append("Weak spots: " + ", ".join(f"{k} {v}" for k, v in w.items()))
    c2m = claim_to_merge(prs, comments, since)
    out.append(f"Claim to merge (median min of {len(c2m)} PRs): {fmt(med(c2m))}")
    bad = bad_files(files)
    out.append(f"Files that do not belong in git: {len(bad)}")
    out += [f"  {p} ({size // 1024} KiB)" for p, size in bad]
    if unanswered is not None:                  # a quality number: each owner comment gets an answer (#971)
        out.append(f"Owner comments without an answer (tools/feedback.py): {len(unanswered)}")
    return "\n".join(out)


def git_files():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True, text=True,
                           check=True).stdout.split("\0")
    return [(p, os.path.getsize(os.path.join(root, p))) for p in paths if p and os.path.isfile(os.path.join(root, p))]


def fetch(since, until=None):
    iso = f"{since:%Y-%m-%dT%H:%M:%SZ}"
    created = f"{iso}..{until:%Y-%m-%dT%H:%M:%SZ}" if until else f">={iso}"   # the Dashboard runs fill 10 pages a day
    runs = []
    for page in range(1, 11):
        rs = api(f"actions/runs?per_page=100&page={page}&created={created}")["workflow_runs"]
        runs += rs
        if len(rs) < 100:
            break
    ci = [r for r in runs if r["name"] == "CI" and r.get("status") == "completed"][:CI_JOB_RUNS]
    jobs = [j for r in ci for j in api(f"actions/runs/{r['id']}/jobs")["jobs"]]
    status = api(f"issues?state=open&labels={STATUS}")
    # one day more: the "Started by" comment of a ticket that merged in the period can be older
    comments = api_pages(f"issues/comments?since={since - datetime.timedelta(days=1):%Y-%m-%dT%H:%M:%SZ}")
    status_comments = [c for c in comments if status and c["issue_url"].endswith(f"/{status[0]['number']}")
                       and c["created_at"] >= iso]
    recent = [c for c in comments if c["created_at"] >= iso or c["body"].startswith("Started by")]
    prs = api_pages("pulls?state=closed&sort=updated&direction=desc", stop=lambda p: p["updated_at"] < iso)
    issues = api_pages(f"issues?state=all&since={iso}")
    events = api_pages("issues/events?", limit=5, stop=lambda e: e["created_at"] < iso)
    return runs, jobs, status_comments, recent, prs, issues, events


def clip(until, runs, status_comments, comments, prs, issues, events):
    """The items up to `until`: a period in the past ends there (--until, #489). A PR that closed later was open."""
    early = lambda t: t is not None and ts(t) < until
    return ([r for r in runs if early(r["created_at"])], [c for c in status_comments if early(c["created_at"])],
            [c for c in comments if early(c["created_at"])], [p for p in prs if early(p.get("closed_at"))],
            [i for i in issues if early(i["created_at"])], [e for e in events if early(e["created_at"])])


def api_pages(path, limit=20, stop=None):
    out = []
    for page in range(1, limit + 1):
        items = api(f"{path}&per_page=100&page={page}")
        out += items
        if len(items) < 100 or (stop and stop(items[-1])):
            break
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--until", type=ts, help="the end of the period (ISO time, default now): compare two periods")
    a = ap.parse_args(argv)
    until = a.until or datetime.datetime.now(datetime.timezone.utc)
    since = until - datetime.timedelta(hours=a.hours)
    runs, jobs, status_comments, comments, prs, issues, events = fetch(since, a.until)
    if a.until:
        runs, status_comments, comments, prs, issues, events = clip(until, runs, status_comments, comments, prs,
                                                                    issues, events)
    files_of = {n: [f["filename"] for f in api(f"pulls/{n}/files?per_page=100")] for n in conflicted(comments)}
    from feedback import fetch as unanswered
    text = report(since, runs, jobs, status_comments, comments, prs, git_files(), files_of, issues, events,
                  unanswered())
    print(text.replace(" UTC", f" UTC until {until:%Y-%m-%d %H:%M} UTC", 1) if a.until else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
