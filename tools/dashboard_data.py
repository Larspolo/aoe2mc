"""Build the data files of the owner's dashboard artifact (aoe2mc Autopilot) from GitHub and the repository.

    python3 tools/dashboard_data.py OUT_DIR

Writes aoe2mc-merged-prs.json, aoe2mc-tickets.json, aoe2mc-epics.json, aoe2mc-roadmap.json, aoe2mc-release-bar.json
and aoe2mc-usage.json, and copies aoe2mc-setup.json (written by hand: tools/dashboard_artifact/setup.json). The page
reads them as attached files. The skill dashboard-refresh uploads them (#982).
"""
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import health  # noqa: E402

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


def merged_prs(pulls):
    rows = sorted((p for p in pulls if p.get("merged_at")), key=lambda p: p["merged_at"])
    return [dict(number=p["number"], title=p["title"], branch=p["head"]["ref"], created_at=p["created_at"],
                 merged_at=p["merged_at"], minutes_open=round((ts(p["merged_at"]) - ts(p["created_at"])).total_seconds() / 60, 1))
            for p in rows]


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
                        process="process" in names, subs_done=subs.get("completed") or 0, subs_total=subs.get("total") or 0))
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


def usage(hours=72):
    return [dict(at=f"{t:%Y-%m-%dT%H:%M:%SZ}", usage=u, resets=f"{r:%Y-%m-%dT%H:%M:%SZ}", runs=k)
            for t, u, r, k in health.samples(health.status_comments(hours=hours))]


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    issues = pages("issues?state=all")
    files = {
        "aoe2mc-merged-prs.json": merged_prs(pages("pulls?state=closed")),
        "aoe2mc-tickets.json": tickets(issues),
        "aoe2mc-epics.json": epics(issues),
        "aoe2mc-roadmap.json": roadmap(open(os.path.join(root, "docs", "ROADMAP.md")).read()),
        "aoe2mc-release-bar.json": release_bar(open(os.path.join(root, "docs", "RELEASE.md")).read()),
        "aoe2mc-usage.json": usage(),
        "aoe2mc-setup.json": json.load(open(os.path.join(root, "tools", "dashboard_artifact", "setup.json"))),
    }
    for name, rows in files.items():
        with open(os.path.join(out_dir, name), "w") as f:
            json.dump(rows, f, ensure_ascii=False)
        print(f"{name}: {len(rows)} rows")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out/dashboard")
