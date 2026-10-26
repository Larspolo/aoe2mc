"""Numbers of the whole system for the `improve` skill: CI, environment, repository and scheduling (#242).

    python3 tools/health.py              # the last 24 hours
    python3 tools/health.py --hours 72

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dashboard import api, closes  # noqa: E402

CI_JOB_RUNS = 20                          # read the step times of this many CI runs (one API call each)
DENY = (".log", ".mca", ".png")           # suffixes that do not belong in git ...
DENY_OK = ("docs/", "samples/")           # ... except .png in these folders
BIG = 1 << 20


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
    """Counts of takeovers, releases and merge conflicts in the issue and PR comments."""
    bodies = [(c.get("body") or "").lstrip() for c in comments]
    return {"takeovers": sum(b.startswith("Taken over by") for b in bodies),
            "releases": sum(b.startswith("Released") for b in bodies),
            "conflicts": sum("the merge failed" in b or "merge conflict" in b.lower() for b in bodies)}


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


SAMPLE = re.compile(r"^Usage: (\S+) · usage (\d+(?:\.\d+)?)% · resets (\S+) · claims (\d+)", re.M)


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


def measured_burn(comments, now, hours=24, need=5):
    """The median burn of the pairs of the last `hours`, or None when there are fewer than `need` pairs."""
    pairs = burn_pairs([s for s in samples(comments) if s[0] >= now - datetime.timedelta(hours=hours)])
    return med(pairs) if len(pairs) >= need else None


def status_comments(hours=24):
    """The comments on the status issue of the last `hours`."""
    status = api("issues?state=open&labels=agent-status")
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    return api_pages(f"issues/{status[0]['number']}/comments?since={since:%Y-%m-%dT%H:%M:%SZ}") if status else []


def active_claims(now, minutes=30):
    """The open tickets with `in-progress` that changed in the last `minutes` (rule 4 of the scheduled task)."""
    return sum(ts(i["updated_at"]) >= now - datetime.timedelta(minutes=minutes)
               for i in api("issues?state=open&labels=in-progress&per_page=100") if "pull_request" not in i)


def fmt(x):
    return "-" if x is None else f"{x:.1f}"


def report(since, runs, jobs, status_comments, comments, prs, files):
    out = [f"Health since {since:%Y-%m-%d %H:%M} UTC", "", "CI runs (count, median min, max min, failures):"]
    for name, (k, m, mx, fail) in ci_runs(runs, since).items():
        out.append(f"  {name}: {k}, {fmt(m)}, {fmt(mx)}, {fail}")
    out.append("Slowest CI steps (median min): " + "; ".join(f"{k} {fmt(m)}" for m, k in slow_steps(jobs)))
    setup = setup_minutes(status_comments)
    out.append(f"Setup (median min of {len(setup)} Metrics lines): {fmt(med(setup))}")
    e = events(comments)
    out.append(f"Takeovers {e['takeovers']}, releases {e['releases']}, merge conflicts {e['conflicts']}")
    b = burn_pairs([x for x in samples(status_comments) if x[0] >= since])
    out.append(f"Burn per run-hour (median of {len(b)} pairs of Usage lines): {'-' if not b else f'{med(b):.3f}'}")
    c2m = claim_to_merge(prs, comments, since)
    out.append(f"Claim to merge (median min of {len(c2m)} PRs): {fmt(med(c2m))}")
    bad = bad_files(files)
    out.append(f"Files that do not belong in git: {len(bad)}")
    out += [f"  {p} ({size // 1024} KiB)" for p, size in bad]
    return "\n".join(out)


def git_files():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True, text=True,
                           check=True).stdout.split("\0")
    return [(p, os.path.getsize(os.path.join(root, p))) for p in paths if p and os.path.isfile(os.path.join(root, p))]


def fetch(since):
    iso = f"{since:%Y-%m-%dT%H:%M:%SZ}"
    runs = []
    for page in range(1, 11):
        rs = api(f"actions/runs?per_page=100&page={page}&created=>={iso}")["workflow_runs"]
        runs += rs
        if len(rs) < 100:
            break
    ci = [r for r in runs if r["name"] == "CI" and r.get("status") == "completed"][:CI_JOB_RUNS]
    jobs = [j for r in ci for j in api(f"actions/runs/{r['id']}/jobs")["jobs"]]
    status = api("issues?state=open&labels=agent-status")
    # one day more: the "Started by" comment of a ticket that merged in the period can be older
    comments = api_pages(f"issues/comments?since={since - datetime.timedelta(days=1):%Y-%m-%dT%H:%M:%SZ}")
    status_comments = [c for c in comments if status and c["issue_url"].endswith(f"/{status[0]['number']}")
                       and c["created_at"] >= iso]
    recent = [c for c in comments if c["created_at"] >= iso or c["body"].startswith("Started by")]
    prs = api_pages("pulls?state=closed&sort=updated&direction=desc", stop=lambda p: p["updated_at"] < iso)
    return runs, jobs, status_comments, recent, prs


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
    a = ap.parse_args(argv)
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=a.hours)
    runs, jobs, status_comments, comments, prs = fetch(since)
    print(report(since, runs, jobs, status_comments, comments, prs, git_files()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
