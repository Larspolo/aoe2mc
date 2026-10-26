"""The tickets that wait for the owner (#983): the open `needs-human` tickets that are not muted, with their kind
and question. The skill `human` (a local session of the owner, `/human`) lists them and prepares the chosen one.

    python3 tools/owner_tasks.py             # decision tickets first, then the oldest first
    python3 tools/owner_tasks.py --show N    # the section "## For the owner" of ticket N (else its last question)
    python3 tools/owner_tasks.py --json      # the list as JSON

Kinds: `decision` ("Decide: ..."), `play` (a play test in Minecraft: "Check ..."), `setting` (the environment, the
scheduled task or GitHub), `outside` (a step outside the cloud), `close` (close an issue that the auto mode did not let
the agent close, #862), `question` (all others). A line "Kind: <kind>" in the
section "## For the owner" wins over the title. Token: GITHUB_TOKEN, else `gh api`. Python standard library only.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dashboard import MUTED, api, labels, pages, question  # noqa: E402

KINDS = ["decision", "play", "setting", "outside", "close", "question"]
OUTSIDE = re.compile(r"\b(own computer|second repository|local session|on your computer|bootstrap)\b", re.I)
CLOSE = re.compile(r"\b(please close|close (this|it) by hand)\b", re.I)
SETTING = re.compile(r"\b(environment|setup script|network|variable|scheduled task|GitHub setting|secret|"
                     r"interaction limit|branch protection)\b", re.I)


def for_owner(body):
    """The text of the section "## For the owner" of an issue body, or ""."""
    m = re.search(r"^## For the owner[ \t]*\n(.*?)(?=^## |\Z)", body or "", re.M | re.S)
    return m.group(1).strip() if m else ""


def kind(issue, comments=()):
    """The kind of a needs-human ticket: the "Kind:" line of "## For the owner", else from the title, the body and
    the last agent request (a close that the auto mode denied, #862)."""
    m = re.search(r"^Kind:\s*(\w+)", for_owner(issue.get("body")), re.M | re.I)
    if m and m.group(1).lower() in KINDS:
        return m.group(1).lower()
    title = issue.get("title") or ""
    if title.startswith("Decide:"):
        return "decision"
    if re.match(r"(Check|Play|Test)\b", title) or "Minecraft client" in (issue.get("body") or ""):
        return "play"
    if SETTING.search(title):
        return "setting"
    if OUTSIDE.search(title):
        return "outside"
    if CLOSE.search(show(issue, list(comments))):
        return "close"
    return "question"


def tasks(issues, comments):
    """The open needs-human tickets that are not muted, decision tickets first, then by number (the oldest first).
    comments: {issue number: comments}."""
    wait = [i for i in issues if "pull_request" not in i and "needs-human" in labels(i) and MUTED not in labels(i)
            and i.get("state", "open") == "open"]
    out = [{"number": i["number"], "title": i["title"], "kind": kind(i, comments.get(i["number"], [])), "epic": "epic" in labels(i),
            "question": ask(i, comments.get(i["number"], [])), "url": i.get("html_url", "")} for i in wait]
    return sorted(out, key=lambda t: (t["kind"] != "decision", t["number"]))


def ask(issue, comments):
    """One line: the last question of the comments, else the first line of what the owner must do."""
    q = question(comments)
    if q != "see ticket":
        return q
    line = next((x.strip() for x in show(issue, comments).splitlines() if x.strip()), "see ticket")
    line = re.sub(r"^@\S+\s*", "", line)
    return line if len(line) <= 120 else line[:117] + "..."


def show(issue, comments):
    """What the owner must do for one ticket: its section "## For the owner", else the last agent comment."""
    text = for_owner(issue.get("body"))
    if text:
        return text
    last = next((c for c in reversed(comments) if "@" in (c.get("body") or "")), comments[-1] if comments else None)
    return (last.get("body") or "").split("\n---\n")[0].strip() if last else (issue.get("body") or "").strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--show", type=int, metavar="N", help="print what the owner must do for ticket N")
    ap.add_argument("--json", action="store_true", help="print the list as JSON")
    a = ap.parse_args(argv)
    if a.show:
        issue = api(f"issues/{a.show}")
        comments = pages(f"issues/{a.show}/comments")
        print(f"#{issue['number']} {issue['title']} ({kind(issue, comments)})\n")
        print(show(issue, comments))
        return 0
    issues = pages("issues?state=open&labels=needs-human")
    comments = {i["number"]: pages(f"issues/{i['number']}/comments") for i in issues if MUTED not in labels(i)}
    found = tasks(issues, comments)
    if a.json:
        print(json.dumps(found, indent=1))
        return 0
    for t in found:
        print(f"#{t['number']} [{t['kind']}{', epic' * t['epic']}] {t['title']} – {t['question']}")
    if not found:
        print("No ticket waits for the owner.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
