"""Set up the agent system in a new repository (#906).

    python3 tools/bootstrap.py TARGET_DIR --repo OWNER/NAME [--branch main] [--github]

Copies the generic files of the table "Generic and specific files" in `docs/SYSTEM.md` (one list for the document and
the tool), with the repository, the owner login and the project name of the new project in place of aoe2mc. Writes
`agent.toml` with the new values and placeholder commands, and short starts of the specific files that the generic
files need (`STUBS`). Prints the setup steps of the owner (`docs/SYSTEM.md`) and the specific files that stay to do.
`--github` also makes the labels of `.github/labels.txt` and the status issue with `gh api` (REST).
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent_config import CONFIG, ROOT  # noqa: E402

SYSTEM = os.path.join(ROOT, CONFIG["docs"]["system"])
ROW = re.compile(r"^\| `([^`]+)` \| (generic|specific) \|", re.M)

CONFIG_TOML = """# Project values of the agent system (#905). The tools in tools/ read this file (tools/agent_config.py).

repo = "{repo}"
owner = "{owner}"
branch = "{branch}"

[status]
issue = 1
label = "agent-status"
paused = "paused"

[pacing]
max_runs = 16                   # the most runs at one time (tools/usage.py)
weights = {{ haiku = 0.25 }}     # a lane run in Opus runs (start value)

[commands]                      # change these to the commands of the project
install = "python3 -m pip install -r requirements-dev.txt"
lint = "ruff check ."
fast = "python3 -m pytest"
slow = "python3 -m pytest -m slow"
server = ""

[docs]
system = "docs/SYSTEM.md"
steering = "docs/STEERING.md"
learnings = "docs/LEARNINGS.md"
roadmap = "docs/ROADMAP.md"
"""

CI = """name: CI

# Quick checks on each PR and on main: Automerge merges a green agent PR (workflow name "CI", job "quick").
on:
  push:
    branches: [{branch}]
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  quick:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: {install}
      - name: Lint
        run: {lint}
      - name: Fast tests
        run: {fast}
"""

STUBS = {   # specific files that the generic files need, as a short start for the new project
    "agent.toml": CONFIG_TOML,
    ".github/workflows/ci.yml": CI,
    ".gitattributes": "# Ticket runs only add lines here, so a merge keeps the new lines of both sides.\n"
                      "docs/LEARNINGS.md merge=union\n",
    "CLAUDE.md": "# {name} – guide for Claude Code\n\nThe owner is **{owner}**. The agent system: `docs/SYSTEM.md`.\n"
                 "The project values: `agent.toml`.\n\n## Commands\n\nTODO: install, lint, tests.\n\n## Code map\n\n"
                 "TODO\n\n{generic}\n@docs/LEARNINGS.md\n",
    "docs/LEARNINGS.md": "# Learnings\n\nThe agent writes here what it learned the hard way. Each line must save time "
                         "in a later session.\n\n## Environment and libraries\n\n## Code\n",
    "docs/ROADMAP.md": "# Roadmap\n\nThe goals of {name} and their features: done (`[x]`) or missing (`[ ]`). "
                       "The `roadmap` skill makes the next epic from a missing feature.\n\n## 1. TODO\n\n"
                       "- [ ] `goal:feature` TODO\n",
}


def table(text):
    """(path, kind) of each row of the table "Generic and specific files" of docs/SYSTEM.md."""
    return ROW.findall(text.split("## Generic and specific files", 1)[1])


def section(text, title):
    """The section "## title" of a Markdown text, up to the next "## " heading."""
    m = re.search(rf"^## {re.escape(title)}\n.*?(?=^## |\Z)", text, re.M | re.S)
    return m.group(0).rstrip() + "\n" if m else ""


def rename(text, repo, name, owner):
    """The text with the repository, the owner login and the project name of the new project. One pass, the longest
    old value first: a new value that contains an old one is not replaced again (#953)."""
    new = {CONFIG["repo"]: repo, CONFIG["owner"]: owner, CONFIG["repo"].split("/")[1]: name}
    return re.sub("|".join(map(re.escape, sorted(new, key=len, reverse=True))), lambda m: new[m[0]], text)


def github_calls(repo, labels, title="Agent status"):
    """The `gh api` arguments that make the labels and the status issue of the new repository."""
    calls = [["gh", "api", f"repos/{repo}/labels", "-f", f"name={n}", "-f", f"color={c}", "-f", f"description={d}"]
             for n, c, d in (line.split("|", 2) for line in labels.splitlines() if line.strip() and not line.startswith("#"))]
    body = '<!-- agent-state: {"last_run": "1970-01-01T00:00:00Z", "runs": 0} -->\n## Agent status\n\n### Process changes\n'
    return calls + [["gh", "api", f"repos/{repo}/issues", "-f", f"title={title}", "-f", f"body={body}",
                     "-f", f"labels[]={CONFIG['status']['label']}"]]


def bootstrap(target, repo, branch="main"):
    """Write the files into target. Returns (copied, written, todo): the generic files, the stubs, the specific files
    that the owner or a first run must write."""
    owner, name = repo.split("/")
    system = open(SYSTEM).read()
    rows = table(system)
    claude = open(os.path.join(ROOT, "CLAUDE.md")).read()
    values = {"repo": repo, "owner": owner, "name": name, "branch": branch, **CONFIG["commands"],
              "generic": section(claude, "How to work") + "\n" + section(claude, "Improve the process")}
    copied, written = [], []
    for path, kind in rows:
        if kind != "generic":
            continue
        src, dst = os.path.join(ROOT, path), os.path.join(target, path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            text = open(src).read()
        except UnicodeDecodeError:
            shutil.copy2(src, dst)
        else:
            with open(dst, "w") as f:
                f.write(rename(text, repo, name, owner))
            shutil.copymode(src, dst)
        copied.append(path)
    for path, text in STUBS.items():
        dst = os.path.join(target, path)
        os.makedirs(os.path.dirname(dst) or target, exist_ok=True)
        with open(dst, "w") as f:
            f.write(rename(text.format(**values), repo, name, owner) if path != "agent.toml" else text.format(**values))
        written.append(path)
    todo = [p for p, k in rows if k == "specific" and p not in STUBS]
    return copied, written, todo


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("target")
    ap.add_argument("--repo", required=True, help="OWNER/NAME of the new repository")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--github", action="store_true", help="also make the labels and the status issue (gh api)")
    a = ap.parse_args(argv)
    if a.repo.count("/") != 1:
        ap.error("--repo must be OWNER/NAME")
    copied, written, todo = bootstrap(a.target, a.repo, a.branch)
    owner, name = a.repo.split("/")
    print(f"Copied {len(copied)} generic files and wrote {len(written)} starts ({', '.join(written)}) to {a.target}.")
    print("\nWrite these specific files for the project (see docs/SYSTEM.md, \"Generic and specific files\"):")
    print("".join(f"- {p}\n" for p in todo))
    print(rename(section(open(SYSTEM).read(), "Setup steps of the owner"), a.repo, name, owner))
    if a.github:
        labels = open(os.path.join(ROOT, ".github/labels.txt")).read()
        for call in github_calls(a.repo, labels):
            r = subprocess.run(call, capture_output=True, text=True)
            print(("ok  " if r.returncode == 0 else "FAIL ") + " ".join(call[:3]) + (f": {r.stderr.strip()}" if r.returncode else ""))


if __name__ == "__main__":
    main()
