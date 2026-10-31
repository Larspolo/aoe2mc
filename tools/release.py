"""Progress of each goal toward its release bar (#878, #879): the rules and items of steering/project/RELEASE.md, the features of
steering/project/ROADMAP.md and the epics on GitHub.

    python3 tools/release.py     # one line for each goal: percent of C, A and B, the tickets left, the due checks

Token: GITHUB_TOKEN. Without it the script uses `gh api` (cloud sessions). Python standard library only.
"""
import math
import os
import re
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "framework", "tools"))     # dashboard (api, pages), moved there by #4195
MILESTONES = "CAB"                                  # C = 100 %; A and B are indications
INCLUDES = {"B": "B", "A": "BA", "C": "BAC"}         # the feature milestones that a milestone counts


def roadmap(text):
    """{key: (goal number, checked, {epic numbers that the line names})} of the feature lines of steering/project/ROADMAP.md."""
    out, goal = {}, 0
    for line in text.splitlines():
        if line.startswith("## ") and line[3:4].isdigit():
            goal = int(line[3])
        elif (m := re.match(r"- \[([ x])\] `([a-z]+:[a-z-]+)`", line)) and goal:
            out[m[2]] = (goal, m[1] == "x", {int(n) for n in re.findall(r"#(\d+)", line)})
    return out


def release(text):
    """(bug reserve share, [(goal number, id, milestone, estimate or None, ticket or None)]) of steering/project/RELEASE.md."""
    share, rows, goal, n = float(re.search(r"Bug reserve: ([\d.]+)", text)[1]), [], 0, 0
    for line in text.splitlines():
        if line.startswith("## "):
            n, goal = (n, 0) if line.startswith("## Rules") else (n + 1, n + 1)
        elif goal and (m := re.match(r"\| `([^`]+)` \| ([ABC]) \| (\d*) *\|[^|]*\| *#?(\d*) *\|", line)):
            rows.append((goal, m[1], m[2], int(m[3]) if m[3] else None, int(m[4]) if m[4] else None))
    return share, rows


def epic_key(body):
    m = re.search(r"Roadmap: `([^`]+)`", body or "")
    return m and m[1]


def progress(features, rows, share, epics, closed=frozenset()):
    """{goal: {milestone: (percent, done, features left, checks left, reserve)}}. features: roadmap(), rows and share:
    release(), epics: [{number, state, body, sub_issues_summary: {total, completed}}], closed: closed issue numbers
    (the check tickets)."""
    median = round(statistics.median([n for e in epics if e["state"] == "closed"
                                      and (n := (e.get("sub_issues_summary") or {}).get("total"))] or [5]))
    item = {r[1]: r for r in rows}
    tally = {}                                      # goal -> milestone -> [done, features left, checks left]
    for key, (goal, checked, named) in features.items():
        own = [e for e in epics if epic_key(e.get("body")) == key or e["number"] in named]
        _, _, ms, est, _ = item.get(key, (goal, key, "C", None, None))
        total = sum((e.get("sub_issues_summary") or {}).get("total", 0) for e in own)
        shut = sum((e.get("sub_issues_summary") or {}).get("completed", 0) for e in own)
        if any(e["state"] == "open" for e in own):
            done, left = shut, max(total, est or median) - shut
        elif own:
            done, left = max(shut, 1), 0
        else:
            done, left = (est or median, 0) if checked else (0, est or median)
        for m in MILESTONES:
            if ms in INCLUDES[m]:
                t = tally.setdefault(goal, {}).setdefault(m, [0, 0, 0])
                t[0], t[1] = t[0] + done, t[1] + left
    out = {}
    for goal, ms in tally.items():
        checks = [r for r in rows if r[0] == goal and r[1] not in features]
        cdone = sum(r[3] or 0 for r in checks if r[4] in closed)
        cleft = sum(r[3] or 0 for r in checks if r[4] not in closed)
        for m, (done, left, _) in ms.items():
            reserve = math.ceil(share * left)
            d, rest = done + cdone, left + cleft + reserve
            out.setdefault(goal, {})[m] = (round(100 * d / (d + rest)) if d + rest else 100, d, left, cleft, reserve)
    return out


def due(features, rows, epics):
    """The rows of release(): the release checks with no ticket whose milestone has 0 features left in their goal
    (#3342). Their check tickets can start: the `roadmap` skill makes them in the next deep run."""
    left = progress(features, rows, 0, epics)
    return [r for r in rows if r[1] not in features and r[4] is None
            and left.get(r[0], {}).get(r[2], (0, 0, 0))[2] == 0]


GOALS = {1: "Convert maps", 2: "Play AoE2", 3: "Replay a game", 4: "Agent system"}


def lines(result):
    out = []
    for goal in sorted(result):
        r = result[goal]
        out.append(f"{GOALS.get(goal, goal)}: " + " · ".join(
            f"{m} {r[m][0]} % ({r[m][2] + r[m][3] + r[m][4]} left = {r[m][2]} + {r[m][3]} + {r[m][4]})"
            for m in MILESTONES if m in r))
    return out


def total(result, m="C"):
    """The percent of milestone m over the game goals together: done ÷ (done + left) of their tickets (#899). Goal 4
    (the agent system, #900) is not a game goal: it does not count."""
    game = [r for g, r in result.items() if g != 4 and m in r]
    done = sum(r[m][1] for r in game)
    rest = sum(r[m][2] + r[m][3] + r[m][4] for r in game)
    return 100 * done / (done + rest) if done + rest else 100.0


def load():
    """(features, share, rows, epics) of the files on disk and the epics on GitHub."""
    from dashboard import pages
    with open(os.path.join(ROOT, "steering", "project", "ROADMAP.md")) as f:
        features = roadmap(f.read())
    with open(os.path.join(ROOT, "steering", "project", "RELEASE.md")) as f:
        share, rows = release(f.read())
    return features, share, rows, pages("issues?labels=epic&state=all")


def current(data=None):
    """progress() of load() (or of its result `data`)."""
    from dashboard import api
    features, share, rows, epics = data or load()
    closed = {r[4] for r in rows if r[4] and api(f"issues/{r[4]}")["state"] == "closed"}
    return progress(features, rows, share, epics, closed)


def due_lines(rows):
    """The text of due(): "<id> (goal, milestone)" for each row."""
    return [f"{r[1]} ({GOALS.get(r[0], r[0])}, {r[2]})" for r in rows]


def main():
    data = load()
    print("Release bar (C = 100 %, milestones A and B; left = features + checks + bug reserve):")
    print("\n".join(lines(current(data))))
    if checks := due_lines(due(data[0], data[2], data[3])):
        print("Release checks with no ticket: " + " · ".join(checks))


if __name__ == "__main__":
    main()
