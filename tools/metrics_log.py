"""The log of the status issue comments on the orphan branch `metrics` (#1983): one file `status/YYYY-MM-DD.jsonl`
per day of `created_at`, one JSON line per comment (`id`, `created_at`, `updated_at`, `issue_url`, `body`).
`tools/health.py` reads the files and only the newest comments from the API, not hundreds of API pages.
The folder `pacer/` holds one JSON line per cycle of the pacer (`pacer.py --log`, `pacer/YYYY-MM-DD.jsonl` by `at`).

    python3 tools/metrics_log.py DIR [--days N]     # DIR: a checkout of the branch `metrics` (metrics.yml)
    python3 tools/metrics_log.py DIR --pacer F --push   # also the pacer records of F; commit and push (pacer.yml)

The pacer loop (`pacer.yml`) runs it in each cycle (10 minutes): the cron of `metrics.yml` ("every 15 minutes") ran
8 times in 38 hours (2026-10-27 to 10-29), and the branch was up to 6 hours old. `metrics.yml` stays as the fallback
and for a backfill. Two writers: `--push` takes the branch again and adds again when the other one pushed first.
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


def add_pacer(root, path):
    """Add the cycle records of the file `path` (`pacer.py --log`: one JSON line per cycle) to the day files
    `pacer/YYYY-MM-DD.jsonl` of `root`, one line per `at`. A line that does not parse is left out. Returns the paths of
    the changed files."""
    try:
        with open(path) as f:
            text = f.read().splitlines()
    except OSError:
        return []
    days = {}
    for x in text:
        try:
            r = json.loads(x)
            days.setdefault(r["at"][:10], {})[r["at"]] = r
        except (ValueError, KeyError, TypeError):
            continue
    changed = []
    for d, rows in sorted(days.items()):
        path = os.path.join(root, "pacer", f"{d}.jsonl")
        old = {}
        if os.path.exists(path):
            with open(path) as f:
                old = {r["at"]: r for r in map(json.loads, filter(str.strip, f))}
        new = {**old, **rows}
        if new != old:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.writelines(json.dumps(new[k], ensure_ascii=False) + "\n" for k in sorted(new))
            changed.append(path)
    return changed


def push(root, pacer=None, days=None, tries=3, remote="origin"):
    """Add the new status comments and the pacer records of the file `pacer` to the checkout `root` of the branch
    `metrics`, commit and push. When another writer pushed first, take its branch and add again (`update` reads from
    the newest stored comment, `add_pacer` by `at`: nothing comes twice). Returns 0, or 1 when no push went through."""
    sh = lambda *a: subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True, timeout=60)
    for _ in range(tries):
        changed = update(root, days) + (add_pacer(root, pacer) if pacer else [])
        if not changed:
            print("no change")
            return 0
        sh("add", "-A", ".")
        sh("-c", "user.name=github-actions[bot]", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
           "commit", "-q", "-m", "Log the status comments and the pacer cycles")
        if sh("push", "-q", remote, f"HEAD:refs/heads/{BRANCH}").returncode == 0:
            print(f"pushed {len(changed)} files")
            return 0
        if sh("fetch", "-q", "--depth", "1", remote, BRANCH).returncode or sh("reset", "-q", "--hard", "FETCH_HEAD").returncode:
            break
    print("no push", file=sys.stderr)
    return 1


def parse(t):
    return datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, timeout=60)


def load(since, remote="origin"):
    """The stored comments created since `since`, from `remote`/metrics, or None when git cannot read the branch."""
    try:  # a hung git call (#3290) reads as a failed one; only the tip: the pacer adds a commit each cycle
        if git("fetch", "-q", "--depth", "1", remote, f"+refs/heads/{BRANCH}:refs/remotes/{remote}/{BRANCH}").returncode:
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
    ap.add_argument("--pacer", metavar="FILE", help="also add the pacer records of FILE (pacer.py --log)")
    ap.add_argument("--push", action="store_true", help="commit and push the branch (again after a push of another writer)")
    a = ap.parse_args(argv)
    if a.push:
        return push(a.dir, a.pacer, a.days)
    for path in update(a.dir, a.days) + (add_pacer(a.dir, a.pacer) if a.pacer else []):
        print(os.path.relpath(path, a.dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
