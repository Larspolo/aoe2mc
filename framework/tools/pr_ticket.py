"""The ticket of a PR for Automerge (#4773): the first closing word of the body, else of the commits (#4122), else
the claim ref that names the PR branch, else a title that ends with "(#N)". A body with "Part of #N"
(`ship_pr.py --part`) keeps its ticket open: no ticket then.

    python3 framework/tools/pr_ticket.py PR.json COMMITS.txt   # prints "N" (body closes it) or "N add" (append "Closes #N")

PR.json is the PR of the REST API; COMMITS.txt has the commit messages. `git ls-remote origin` reads the claim refs."""
import json
import re
import subprocess
import sys

CLOSE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?) #(\d+)", re.I)


def ticket(body, commits, title, claims):
    """(N, add) of the PR, or (None, False). `claims`: {ticket: subject of its claim tip}; add: the body lacks it."""
    body = body or ""
    if m := CLOSE.search(body):
        return int(m.group(1)), False
    if re.search(r"\bPart of #\d+", body, re.I):
        return None, False
    if m := CLOSE.search(commits or ""):
        return int(m.group(1)), True
    return found(claims) or title_ticket(title)


def found(claims):
    """The ticket of a claim or beat line that names the branch ("Claim #N by <branch> (...)")."""
    for n, line in sorted(claims.items()):
        if line:
            return n, True
    return None


def title_ticket(title):
    m = re.search(r"\(#(\d+)\)\s*$", title or "")
    return (int(m.group(1)), True) if m else (None, False)


def branch_claims(tips, branch):
    """{ticket: subject} of the claim tips whose Claim or Beat line names `branch`."""
    return {n: s for n, s in tips.items() if s.split(" ")[0] in ("Claim", "Beat") and s.split(" ")[3:4] == [branch]}


def remote_tips(remote="origin"):
    """{ticket: subject} of the highest claim slot of each ticket."""
    top = {}
    for line in subprocess.run(["git", "ls-remote", remote, "refs/heads/claim/*"], capture_output=True, text=True,
                               check=True).stdout.splitlines():
        sha, ref = line.split("\t")
        m = re.fullmatch(r"refs/heads/claim/(\d+)(?:-(\d+))?", ref)
        if m and int(m.group(2) or 1) >= top.get(int(m.group(1)), (0, "", ""))[0]:
            top[int(m.group(1))] = (int(m.group(2) or 1), sha, ref)
    if not top:
        return {}
    subprocess.run(["git", "fetch", "-q", remote, *[ref for _, _, ref in top.values()]], check=True)
    return {n: subprocess.run(["git", "log", "-1", "--format=%s", sha], capture_output=True, text=True,
                              check=True).stdout.strip() for n, (_, sha, _) in top.items()}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    with open(argv[0]) as f:
        pr = json.load(f)
    with open(argv[1]) as f:
        commits = f.read()
    body, title = pr.get("body") or "", pr.get("title") or ""
    claims = {}
    if not CLOSE.search(body + "\n" + commits) and not re.search(r"\bPart of #\d+", body, re.I):
        claims = branch_claims(remote_tips(), pr["head"]["ref"])
    n, add = ticket(body, commits, title, claims)
    if n:
        print(f"{n} add" if add else n)


if __name__ == "__main__":
    main()
