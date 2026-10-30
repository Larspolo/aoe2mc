"""Build the data files of the owner's dashboard artifact (aoe2mc Autopilot) from GitHub and the repository.

    python3 tools/dashboard_data.py OUT_DIR

Writes aoe2mc-merged-prs.json, aoe2mc-tickets.json, aoe2mc-epics.json, aoe2mc-roadmap.json, aoe2mc-release-bar.json,
aoe2mc-usage.json and aoe2mc-tokens.json, and copies aoe2mc-setup.json (written by hand: tools/dashboard_artifact/setup.json). The page
reads them as data files: `tools/dashboard_site.py` builds the GitHub Pages site with them (#982).

With `DASHBOARD_CACHE` (a folder that `dashboard-site.yml` keeps with `actions/cache`), it reads only the issues and
PRs that changed since the last build (`cached`): all issues and all closed PRs were about 60 API pages in each build,
6 builds an hour, and the REST limit of the workflow token ran out (2026-10-29). Once a day it reads all again.
"""
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import health  # noqa: E402

DATASETS = {"merges": "aoe2mc-merged-prs.json", "tickets": "aoe2mc-tickets.json", "epics": "aoe2mc-epics.json",
            "roadmap": "aoe2mc-roadmap.json", "release_bar": "aoe2mc-release-bar.json", "usage": "aoe2mc-usage.json",
            "tokens": "aoe2mc-tokens.json", "setup": "aoe2mc-setup.json"}
ROWS = re.compile(r"\s*\.(filter|find|some|every|forEach|map|flatMap|sort)\(\s*\(?\s*(\w+)(?:\s*,\s*(\w+))?\s*\)?\s*=>")

GOALS = {"1": "convert", "2": "play", "3": "replay", "4": "system"}
SECTIONS = {"Convert maps": "convert", "Play AoE2": "play", "Replay a game": "replay", "The agent system": "system"}
KEY = re.compile(r"Roadmap:\s*`([a-z0-9:-]+)`")


def pages(path):
    out, page = [], 1
    while True:
        part = health.api(f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}")
        out += part
        if len(part) < 100:
            return out
        page += 1


def ts(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


FULL_HOURS = 24             # a cache older than this reads all issues and PRs again (deleted or missed items)
OVERLAP = 120               # seconds: the next read starts this much before the start of this read


def slim(item):
    """The fields of an issue or a PR that the data files use: a small cache. The body only for an epic (`KEY`)."""
    names = [label["name"] for label in item.get("labels") or []]
    out = {k: item.get(k) for k in ("number", "title", "state", "created_at", "closed_at", "merged_at", "updated_at",
                                    "sub_issues_summary", "parent_issue_url")}
    out["labels"] = [{"name": n} for n in names]
    out["body"] = (item.get("body") or "") if "epic" in names else ""
    if "pull_request" in item:
        out["pull_request"] = {}
    if "head" in item:
        out["head"] = {"ref": item["head"]["ref"]}
    return out


def cached(folder, now=None, read=None):
    """(issues, closed PRs) as `pages` gives them, from the cache in `folder` and the items that changed since its
    last read: `issues?since=` and the closed PRs by update time until an older one. No cache, or a cache older than
    FULL_HOURS: all of them. Writes the cache back."""
    now, read = now or dt.datetime.now(dt.timezone.utc), read or pages
    path = os.path.join(folder, "items.json")
    try:
        with open(path) as f:
            c = json.load(f)
    except (OSError, ValueError):
        c = {}
    start = f"{now - dt.timedelta(seconds=OVERLAP):%Y-%m-%dT%H:%M:%SZ}"
    full = not c or c.get("full_at", "") < f"{now - dt.timedelta(hours=FULL_HOURS):%Y-%m-%dT%H:%M:%SZ}"
    issues, pulls = ({}, {}) if full else (c["issues"], c["pulls"])
    if full:
        new_issues, new_pulls = read("issues?state=all"), read("pulls?state=closed")
    else:
        new_issues = read(f"issues?state=all&since={c['since']}&sort=updated&direction=asc")
        new_pulls, page = [], 1
        while True:                                 # newest update first: stop at the first one before `since`
            part = health.api(f"pulls?state=closed&sort=updated&direction=desc&per_page=100&page={page}")
            new_pulls += [p for p in part if p["updated_at"] >= c["since"]]
            if len(part) < 100 or part[-1]["updated_at"] < c["since"]:
                break
            page += 1
    issues.update({str(i["number"]): slim(i) for i in new_issues})
    pulls.update({str(p["number"]): slim(p) for p in new_pulls})
    os.makedirs(folder, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"since": start, "full_at": start if full else c["full_at"], "issues": issues, "pulls": pulls}, f)
    return list(issues.values()), list(pulls.values())


def merged_prs(pulls):
    rows = sorted((p for p in pulls if p.get("merged_at")), key=lambda p: p["merged_at"])
    return [dict(number=p["number"], title=p["title"], branch=p["head"]["ref"], created_at=p["created_at"],
                 merged_at=p["merged_at"], minutes_open=round((ts(p["merged_at"]) - ts(p["created_at"])).total_seconds() / 60, 1))
            for p in rows]


def parent(issue):
    """The number of the epic of a sub-issue, else None: the history of the progress needs it."""
    url = issue.get("parent_issue_url")
    return int(url.rsplit("/", 1)[1]) if url else None


def tickets(issues):
    def pick(names, options):
        return next((n for n in names if n in options), "")
    out = []
    for i in sorted((i for i in issues if "pull_request" not in i), key=lambda i: i["number"]):
        names = [label["name"] for label in i["labels"]]
        subs = i.get("sub_issues_summary") or {}
        out.append(dict(number=i["number"], title=i["title"], state=i["state"], created_at=i["created_at"],
                        closed_at=i["closed_at"] or "", priority=pick(names, ("P0", "P1", "P2", "P3")),
                        kind=pick(names, ("bug", "feature", "tooling", "design", "docs", "cleanup")),
                        size=pick(names, ("size:S", "size:M", "size:L")).replace("size:", ""),
                        epic="epic" in names, status_issue="agent-status" in names, needs_human="needs-human" in names,
                        in_progress="in-progress" in names, blocked="blocked" in names, muted="muted" in names,
                        process="process" in names, haiku="lane:haiku" in names, subs_done=subs.get("completed") or 0,
                        subs_total=subs.get("total") or 0, parent=parent(i)))
    return out


def epics(issues):
    """The epics with the roadmap key of their body; the roadmap lines name the other epics of a feature."""
    out = []
    for i in issues:
        if "pull_request" in i or "epic" not in {label["name"] for label in i["labels"]}:
            continue
        subs = i.get("sub_issues_summary") or {}
        m = KEY.search(i.get("body") or "")
        out.append(dict(number=i["number"], title=i["title"], state=i["state"], closed_at=i["closed_at"] or "",
                        key=m[1] if m else "", subs_done=subs.get("completed") or 0, subs_total=subs.get("total") or 0))
    return sorted(out, key=lambda e: e["number"])


def roadmap(text):
    out, goal, order = [], None, 0
    for line in text.splitlines():
        h = re.match(r"## (\d)\. ", line)
        if h or line.startswith("## "):
            goal = GOALS.get(h[1]) if h else None
            continue
        f = re.match(r"- \[([ x])\] `([a-z0-9:-]+)` (.*)", line)
        if goal and f:
            order += 1
            feature = re.sub(r"\s*\((?:epic )?#[^)]*\)", "", f[3]).replace("`", "").strip()
            out.append(dict(id=f[2], goal=goal, order=order, key=f[2], feature=feature, checked=f[1] == "x",
                            refs=" ".join(re.findall(r"#(\d+)", f[3]))))
    return out


def release_bar(text):
    share = float(re.search(r"Bug reserve:\s*([\d.]+)", text)[1])
    out, goal = [], None
    for line in text.splitlines():
        h = re.match(r"## (.+)", line)
        if h:
            goal = SECTIONS.get(h[1].strip())
            continue
        r = re.match(r"\|\s*`([^`]+)`\s*\|\s*([BAC])\s*\|\s*([\d.]*)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$", line)
        if goal and r:
            ticket = re.search(r"\d+", r[5])
            out.append(dict(goal=goal, id=r[1], kind="check" if "-check-" in r[1] else "feature", level=r[2],
                            estimate=float(r[3]) if r[3] else None, title=r[4], share=None, ticket=ticket[0] if ticket else None))
    out += [dict(goal=g, id=f"{g}-bugs", kind="reserve", level="C", estimate=None, share=share, ticket=None,
                 title=f"Bug hunt and fixes (reserve: {round(share * 100)} % of the feature tickets left)") for g in SECTIONS.values()]
    return out


WEEK = dt.timedelta(days=7)
WEEK_RESET = re.compile(r"^Usage: (\S+) · .*?· week resets (\S+)", re.M)
WEEK_SLACK = 0.10       # "behind" when more than this share of the week stays unused at the reset


def week_track(used, reset, now, rate):
    """The on-track text of the 7-day usage `used` (0..1) at `now`, with the 7-day reset `reset` and the measured
    rise per hour `rate` (#1696): "on track", "ahead: runs out <day hh:mm>" or "behind: <n> % unused at the reset"."""
    at = used + rate * (reset - now).total_seconds() / 3600
    if at > 1:
        return f"ahead: runs out {now + dt.timedelta(hours=(1 - used) / rate):%a %H:%M}"
    if at < 1 - WEEK_SLACK:
        return f"behind: {round((1 - at) * 100)} % unused at the reset"
    return "on track"


def week_rate(points, now, hours=24):
    """The rise of the 7-day usage per hour over the points [(time, used)] of the last `hours` up to `now` (a drop is
    the reset), or None with less than one hour of points."""
    pts = [p for p in points if now - dt.timedelta(hours=hours) <= p[0] <= now]
    span = (pts[-1][0] - pts[0][0]).total_seconds() / 3600 if pts else 0
    return sum(max(0, b[1] - a[1]) for a, b in zip(pts, pts[1:])) / span if span >= 1 else None


def usage(hours=168, comments=None):   # 7 days: the chart "Merges per point of 7-day usage" shows all of it
    """The `Usage:` lines: the 5-hour usage, all runs `runs` and the Haiku lane runs `haiku` (#1727), and the 7-day
    usage `week` with its reset `week_resets` and the on-track text `track` where the line has the week (#1696), else
    None. A line before #1696 has no 7-day reset: the reset of another line moved by whole weeks (the 7-day window is
    fixed)."""
    comments = health.status_comments(hours=hours) if comments is None else comments
    week = {t: w / 100 for t, w, _ in health.weekly(comments)}
    known = sorted({health.ts(r) for c in comments for _, r in WEEK_RESET.findall(c.get("body") or "")})
    points, rows = sorted(week.items()), []
    for t, u, r, k, lanes in health.raw_samples(comments):          # the runs, not the Opus runs of the pacing
        row = dict(at=f"{t:%Y-%m-%dT%H:%M:%SZ}", usage=u, resets=f"{r:%Y-%m-%dT%H:%M:%SZ}", runs=k,
                   haiku=lanes.get("haiku", 0), week=week.get(t), week_resets=None, track=None)  # each column (check)
        if t in week and known:
            reset = known[-1] - WEEK * ((known[-1] - t) // WEEK)
            rate = week_rate(points, t)
            row.update(week=week[t], week_resets=f"{reset:%Y-%m-%dT%H:%M:%SZ}",
                       track=None if rate is None else week_track(week[t], reset, t, rate))
        rows.append(row)
    return rows


TOKEN_LINE = re.compile(r"^Tokens: (\d+(?:\.\d+)?)M eq · calls (\d+) · .*?· peak (\d+)k(?: .*?sinks base (\d+)%)?", re.M)
RESULT = re.compile(r"^Metrics: ticket #\d+ · [^·]* · (merged|pr #\d+)", re.M)


def tokens(hours=168, comments=None):
    """The cost of each run report with a `Tokens:` line (tools/tokens.py): its M eq, calls, peak context in k tokens,
    the share 0..1 of the sink `base` (None when not in the top sinks) and its PRs (the `Metrics:` lines with the
    result `merged` or `pr #N`). The chart "Usage per merged PR" divides the eq by the PRs (owner, 2026-10-29)."""
    comments = health.status_comments(hours=hours) if comments is None else comments
    rows = []
    for c in comments:
        body = c.get("body") or ""
        m = TOKEN_LINE.search(body)
        if m and c.get("created_at"):
            rows.append(dict(at=c["created_at"], eq=float(m[1]), calls=int(m[2]), peak=int(m[3]),
                             base=int(m[4]) / 100 if m[4] else None, prs=len(RESULT.findall(body))))
    return sorted(rows, key=lambda r: r["at"])


RUN_LINE = re.compile(r"^Run: .*$", re.M)
WEEK_USED = re.compile(r" · week (\d+(?:\.\d+)?)%")


def accounts(hours=168, comments=None):
    """One row per Claude account (#4239): its last 5-hour usage, 7-day usage and runs (the last `Usage:` line of the
    account), its merged PRs and tokens per merged PR. A `Run:` line names the account of its report (`health.line_account`:
    a line with no account word belongs to the first account). Values of an account with no line are None."""
    comments = health.status_comments(hours=hours) if comments is None else comments
    rows = {}
    for c in sorted(comments, key=lambda c: c.get("created_at") or ""):
        body = c.get("body") or ""
        run = RUN_LINE.search(body)
        owner = health.line_account(run[0]) if run else health.first_account()
        for line in body.splitlines():
            m = health.SAMPLE.match(line) if line.startswith("Usage:") else None
            if m:
                week = WEEK_USED.search(line)
                rows.setdefault(health.line_account(line), {}).update(
                    five_hour=float(m[2]) / 100, runs=int(m[4]), week=float(week[1]) / 100 if week else None)
        t = TOKEN_LINE.search(body)
        if t:
            acc = rows.setdefault(owner, {})
            acc["eq"], acc["prs"] = acc.get("eq", 0) + float(t[1]), acc.get("prs", 0) + len(RESULT.findall(body))
    return [dict(account=name, five_hour=r.get("five_hour"), week=r.get("week"), runs=r.get("runs"),
                 merged=r.get("prs", 0), tokens_per_pr=r["eq"] / r["prs"] if r.get("prs") else None)
            for name, r in sorted(rows.items(), key=lambda x: str(x[0]))]


def close(text, i):
    """The index after the parenthesis that closes the one before index i."""
    depth = 1
    while depth and i < len(text):
        depth += {"(": 1, ")": -1}.get(text[i], 0)
        i += 1
    return i


def fields(body, rows):
    """The fields that the lambdas of `rows.filter((r) => ...)` (and the filters and sorts after it) read of a row."""
    out = set()
    for m in re.finditer(r"(?<![\w.])" + re.escape(rows) + r"(?=\.\w+\()", body):
        i, rest = m.end(), re.match(r"\.(concat|slice)\(", body[m.end():]) is not None  # keep the rows
        while (f := ROWS.match(body, i)):
            end = close(body, body.index("(", i) + 1)
            for v in filter(None, f.groups()[1:]):
                out |= set(re.findall(r"(?<![\w.])" + v + r"\.(\w+)", body[f.end():end]))
            rest, i = f[1] in ("filter", "sort"), end
            if not rest:
                break
        alias = re.search(r"const (\w+) = $", body[:m.start()])
        if rest and alias and alias[1] != rows:  # const open = tickets.filter(...): the rows of `open` too
            out |= fields(body, alias[1])
    return out


def page_columns(page):
    """{dataset: the columns that the dashboard page reads} for the data files (#1031): the inputs of `dash.calc`,
    `dash.data('NAME').data`, and the `data-field` heads of a table with `data-source`."""
    out = {name: set() for name in DATASETS}
    calcs = list(re.finditer(r"dash\.calc\('\w+',\s*\{\s*inputs:\s*\[([^\]]*)\].*?fn:\s*\(([^)]*)\)\s*=>", page, re.S))
    for m, after in zip(calcs, calcs[1:] + [None]):
        body = page[m.end():after.start() if after else len(page)]
        for name, param in zip(re.findall(r"\w+", m[1]), re.findall(r"\w+", m[2])):
            if name in out:
                out[name] |= fields(body, param)
    for m in re.finditer(r"const (\w+) = dash\.data\('(\w+)'\)", page):
        if m[2] in out:
            end = page.find("\n  function ", m.end())
            out[m[2]] |= fields(page[m.end():end if end > 0 else len(page)], m[1] + ".data")
    for m in re.finditer(r'<table[^>]*data-source="(\w+)".*?</table>', page, re.S):
        if m[1] in out:
            out[m[1]] |= set(re.findall(r'data-field="(\w+)"', m[0]))
    return out


def check(out_dir, page):
    """The columns that the page reads and a data file does not have: [(file, [column, ...])]."""
    missing = []
    for name, cols in page_columns(page).items():
        rows = json.load(open(os.path.join(out_dir, DATASETS[name])))
        have = set().union(*(r.keys() for r in rows)) if rows else cols
        if cols - have:
            missing.append((DATASETS[name], sorted(cols - have)))
    return missing


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    folder = os.environ.get("DASHBOARD_CACHE")
    issues, pulls = cached(folder) if folder else (pages("issues?state=all"), pages("pulls?state=closed"))
    files = {
        "aoe2mc-merged-prs.json": merged_prs(pulls),
        "aoe2mc-tickets.json": tickets(issues),
        "aoe2mc-epics.json": epics(issues),
        "aoe2mc-roadmap.json": roadmap(open(os.path.join(root, "steering", "project", "ROADMAP.md")).read()),
        "aoe2mc-release-bar.json": release_bar(open(os.path.join(root, "steering", "project", "RELEASE.md")).read()),
        "aoe2mc-usage.json": usage(),
        "aoe2mc-tokens.json": tokens(),
        "aoe2mc-accounts.json": accounts(),
        "aoe2mc-setup.json": json.load(open(os.path.join(root, "tools", "dashboard_artifact", "setup.json"))),
    }
    for name, rows in files.items():
        with open(os.path.join(out_dir, name), "w") as f:
            json.dump(rows, f, ensure_ascii=False)
        print(f"{name}: {len(rows)} rows")
    missing = check(out_dir, open(os.path.join(root, "tools", "dashboard_artifact", "index.html")).read())
    for name, cols in missing:
        print(f"{name}: the page reads missing columns: {', '.join(cols)}")
    print("columns: missing" if missing else "columns: OK")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "out/dashboard"))
