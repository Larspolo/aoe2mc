"""The log of the status issue comments on the orphan branch `metrics` (#1983): one file `status/YYYY-MM-DD.jsonl`
per day of `created_at`, one JSON line per comment (`id`, `created_at`, `updated_at`, `issue_url`, `body`).
`tools/health.py` reads the files and only the newest comments from the API, not hundreds of API pages.

    python3 tools/metrics_log.py DIR [--days N]     # DIR: a checkout of the branch `metrics` (metrics.yml)

The workflow `metrics.yml` runs it every 15 minutes, one run at a time: parallel runs never push to the branch.
An `issue_comment` trigger would start one Actions run for each comment of the repository (about 1100 a day).
"""
import argparse
import datetime
import glob
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dashboard import STATUS, api  # noqa: E402

BRANCH = "metrics"
KEYS = ("id", "created_at", "updated_at", "issue_url", "body")
UTC = datetime.timezone.utc
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def iso(t):
    return f"{t:%Y-%m-%dT%H:%M:%SZ}"


def day(c):
    return c["created_at"][:10]


def api_comments(since):
    """The status issue comments that changed since `since` (the API `since` is the `updated_at`)."""
    status = api(f"issues?state=open&labels={STATUS}")
    if not status:
        return []
    out = []
    for page in range(1, 1000):
        items = api(f"issues/{status[0]['number']}/comments?since={iso(since)}&per_page=100&page={page}")
        out += items
        if len(items) < 100:
            return out
    return out


def read_dir(root):
    """{id: comment} of the files in `root`."""
    out = {}
    for path in sorted(glob.glob(os.path.join(root, "status", "*.jsonl"))):
        with open(path) as f:
            for line in f:
                if line.strip():
                    c = json.loads(line)
                    out[c["id"]] = c
    return out


def newest(comments):
    """The newest `updated_at` of the comments, or None."""
    return max((c["updated_at"] for c in comments), default=None)


def add(root, comments):
    """Add or replace the comments by `id` in the day files of `root`. Returns the paths of the changed files."""
    old = read_dir(root)
    days = {}
    for c in comments:
        c = {k: c.get(k) for k in KEYS}
        if old.get(c["id"]) != c:
            old[c["id"]] = c
            days[day(c)] = True
    changed = []
    for d in sorted(days):
        path = os.path.join(root, "status", f"{d}.jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        rows = sorted((c for c in old.values() if day(c) == d), key=lambda c: (c["created_at"], c["id"]))
        with open(path, "w") as f:
            f.writelines(json.dumps(c, ensure_ascii=False) + "\n" for c in rows)
        changed.append(path)
    return changed


def update(root, days=None, now=None):
    """Read the comments since the newest stored `updated_at` and add them. `days`, or an empty branch: read the
    comments of the last `days` (default 7) again (a backfill, a repair)."""
    now = now or datetime.datetime.now(UTC)
    last = newest(read_dir(root).values())
    since = parse(last) if last and days is None else now - datetime.timedelta(days=days or 7)
    return add(root, api_comments(since))


def parse(t):
    return datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, timeout=60)


def load(since, remote="origin"):
    """The stored comments created since `since`, from `remote`/metrics, or None when git cannot read the branch."""
    try:  # a hung git call (#3290) reads as a failed one
        if git("fetch", "-q", remote, f"+refs/heads/{BRANCH}:refs/remotes/{remote}/{BRANCH}").returncode:
            return None
        out, d = [], since.date()
        while d <= datetime.datetime.now(UTC).date():
            r = git("show", f"{remote}/{BRANCH}:status/{d:%Y-%m-%d}.jsonl")
            out += [json.loads(line) for line in r.stdout.splitlines() if line.strip()] if r.returncode == 0 else []
            d += datetime.timedelta(days=1)
    except subprocess.TimeoutExpired:
        return None
    return [c for c in out if c["created_at"] >= iso(since)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dir", help="a checkout of the branch metrics")
    ap.add_argument("--days", type=int, help="read the comments of the last N days again (an empty branch: 7)")
    a = ap.parse_args(argv)
    for path in update(a.dir, a.days):
        print(os.path.relpath(path, a.dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
