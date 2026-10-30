"""Ship a ticket in one call: checks, commit, guard, push, PR and its merge state (owner, 2026-10-28).

The first push of a ticket took 2 to 6 tool calls in each run on 2026-10-28, and one run pushed a failed test:
`pytest | tail -1 && git commit && ... && git push` read the exit code of `tail`. This tool reads each exit code.

    python3 framework/tools/ship_pr.py N --message MSG.txt --title "Title" --body BODY.md   # the first push of ticket N
    python3 framework/tools/ship_pr.py N --message MSG.txt                                  # a later push to the open PR

Steps: `git commit -F MSG.txt` of the staged files (without `--message`: the commits that are there), `ruff check .`,
the tests (the test files of the branch and the test files that import its changed modules, never the full
suite: the quick CI runs it, owner #4187; `--tested`: you ran them on this tree), `claim.py N --guard` and the push (`merge_main.push`), the PR (a new
one with `Closes #N` in its body; or the open PR of the branch), and `mergeable_state` (`dirty`: run
`python3 framework/tools/merge_main.py --push N`). Exit 0: shipped. Exit 2: ruff or a test fails, or a change of data
files only adds a test (`docs/extend.md`; nothing pushed). Exit 3: the
guard or the push fails (do not push by hand). Exit 4: no commit to ship, or the PR call fails.
"""
import argparse
import glob
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claim  # noqa: E402
import dashboard  # noqa: E402
import merge_main  # noqa: E402
from agent_config import CONFIG  # noqa: E402

push = merge_main.push
DATA = ("data/", "game/data/", "tools/mcdata/")      # data files: a change there needs no test (owner, 2026-10-29)


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def data_only_tests(changed):
    """The test files of a change that else changes only data files and docs, or []. Such a test checks the content of
    the data: a change of the data must not make a test fail (owner, 2026-10-29, #4242)."""
    tests = [f for f in changed if f.startswith(("tests/", "framework/tests/"))]
    rest = [f for f in changed if not f.startswith(("tests/", "framework/tests/")) and not f.endswith(".md")]
    return tests if tests and rest and all(f.startswith(DATA) for f in rest) else []


def checks():
    """ruff, then the test files of the branch and of its changed modules (more than `MAX_TESTS`: only the branch's).
    Never the full fast suite: the quick CI runs it on each push (owner, #4187). True when all pass."""
    r = subprocess.run(["ruff", "check", "."], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:])
        return False
    changed = git("diff", "--name-only", f"origin/{CONFIG['branch']}...HEAD").stdout.split()
    tests = {f: open(f, encoding="utf-8").read() for f in glob.glob("tests/test_*.py") + glob.glob("framework/tests/test_*.py")}
    run = merge_main.test_files(changed, changed, tests)[0]
    if not run:
        print("no test file of the branch: the quick CI runs the fast suite")
        return True
    par = ["-n", "auto"] if len(run) > 8 else []           # a few files start faster without xdist (verify)
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", *par, *run], capture_output=True, text=True)
    print("\n".join((r.stdout + r.stderr).strip().splitlines()[-15:]))
    return r.returncode == 0


def body_with_ticket(text, number, part=False):
    """The PR body with `Closes #N`: Automerge takes the first closing word as the ticket (#984). part: `Part of #N`,
    no closing word: the ticket stays open (a check ticket that waits for its bug tickets, #3324)."""
    if part:
        return text if f"Part of #{number}" in text else f"{text.rstrip()}\n\nPart of #{number}\n"
    return text if claim.closes(number).search(claim.prose(text)) else f"{text.rstrip()}\n\nCloses #{number}\n"


def state(number, tries=6, wait=5):
    """`mergeable_state` of PR `number`; GitHub computes it after a push (`unknown` or None for some seconds)."""
    for _ in range(tries):
        s = dashboard.api(f"pulls/{number}").get("mergeable_state")
        if s not in (None, "unknown"):
            return s
        time.sleep(wait)
    return "unknown"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("number", type=int, help="the ticket")
    ap.add_argument("--message", help="a file with the commit message: commit the staged files first")
    ap.add_argument("--title", help="the PR title (a new PR)")
    ap.add_argument("--body", help="a file with the PR body (a new PR)")
    ap.add_argument("--tested", action="store_true", help="the checks of `verify` level 1 passed on this tree")
    ap.add_argument("--hold", action="store_true", help="add the label `hold`: Automerge waits for the PR's own checks")
    ap.add_argument("--part", action="store_true", help="`Part of #N` in place of `Closes #N` in a new PR: the ticket "
                    "stays open (a check ticket that waits for its bug tickets, autopilot `owner.md`)")
    a = ap.parse_args(argv)
    branch = git("branch", "--show-current").stdout.strip()
    if a.message:
        c = git("commit", "-q", "-F", a.message)
        if c.returncode:
            print(f"commit failed: {(c.stdout + c.stderr).strip()}")
            return 4
    if not int(git("rev-list", "--count", f"origin/{CONFIG['branch']}..HEAD").stdout.strip() or 0):
        print(f"no commit on {branch} that is not on {CONFIG['branch']}: nothing to ship")
        return 4
    owner = CONFIG["repo"].split("/")[0]
    pr = next(iter(dashboard.api(f"pulls?head={owner}:{branch}&state=open")), None)
    changed = git("diff", "--name-only", f"origin/{CONFIG['branch']}...HEAD").stdout.split()
    if bad := data_only_tests(changed):                  # also with --tested
        print(f"a change of data files only must not add or change tests: remove {' '.join(bad)} (docs/extend.md)")
        return 2
    if not a.tested and not checks():
        return 2
    if not push(a.number):
        return 3
    if pr is None:
        if not (a.title and a.body):
            print(f"pushed, but no PR: give --title and --body (a new PR of #{a.number})")
            return 4
        try:
            pr = dashboard.api("pulls", "POST", {"title": a.title, "head": branch, "base": CONFIG["branch"],
                                                  "body": body_with_ticket(open(a.body, encoding="utf-8").read(), a.number, a.part)})
        except Exception as e:
            print(f"pushed, but the PR call failed ({e}): open the PR with `gh api` (`github.md`)")
            return 4
        print(f"opened PR #{pr['number']}: {pr.get('html_url', '')}")
    else:
        print(f"pushed to PR #{pr['number']}")
    if a.hold:                                  # at once: the quick CI of the PR must not merge it first
        dashboard.api(f"issues/{pr['number']}/labels", "POST", {"labels": ["hold"]})
        print(f"label hold on PR #{pr['number']}")
    s = state(pr["number"])
    print(f"mergeable_state {s}" + (f": run `python3 framework/tools/merge_main.py --push {a.number}`" if s == "dirty" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
