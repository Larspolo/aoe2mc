"""Claim a ticket with a git ref, so that two runs cannot take the same ticket (#211).

A comment or a label never fails when another run was first. A push without force to a new ref fails when the
ref exists, so the ref `claim/N` decides who owns ticket N. The claim commit has no parent and a unique message:
a second push of another claim commit is never a fast-forward. Later claims of the same ticket use
`claim/N-2`, `claim/N-3` ...: the ref with the highest number owns the ticket.

    python3 tools/claim.py N              # claim ticket N; exit 0: yours, exit 1: another run owns it
    python3 tools/claim.py N --release    # give your claim back (needs-human, blocked, hand-off)
    python3 tools/claim.py N --takeover   # take the ticket from a dead run (autopilot "Runs can overlap")
    python3 tools/claim.py N --show       # print the claim refs and the owner
    python3 tools/claim.py N --beat       # show that the own run is alive (at least every 20 minutes)
    python3 tools/claim.py N --stale      # exit 0: the owner made no claim or beat for 30 minutes (stopped run)
    python3 tools/claim.py N --guard      # before each push: beat, and exit 1 when a PR of another branch closes N

Two runs did one ticket (#288): one commented "Started by" and worked without the claim ref. So a claim also fails
when another branch commented "Started by" in the last 30 minutes, and `--guard` stops a run before its push when
it does not own the claim or another branch has a PR for the ticket. The GitHub checks run only for a GitHub remote.

A usage limit stops all runs at about the same time, and a stopped run never continues (#231). Its last beat is
before the stop, so its ticket is stale at most 30 minutes after the limit resets. A live run beats again.

Exit 2: git failed for another reason (network, permission). The workflow `claims.yml` deletes the refs
of a closed ticket: the session proxy gives 403 for branch deletes.
"""
import argparse
import datetime
import re
import subprocess
import sys
import time
import uuid

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
STALE = 30 * 60             # seconds without a claim or beat: the run stopped (usage limit, crash)
RECENT = 30 * 60            # seconds: a "Started by" comment of another branch owns the ticket for this time (#288)


def git(*args, check=True):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def slot(number, k):
    return f"claim/{number}" if k == 1 else f"claim/{number}-{k}"


def refs(number, remote="origin"):
    """{k: sha} of the refs claim/N (k = 1) and claim/N-k on the remote."""
    out = git("ls-remote", remote, f"refs/heads/claim/{number}", f"refs/heads/claim/{number}-*").stdout
    found = {}
    for line in out.splitlines():
        sha, ref = line.split("\t")
        m = re.fullmatch(rf"refs/heads/claim/{number}(?:-(\d+))?", ref)
        if m:
            found[int(m.group(1) or 1)] = sha
    return found


def subject(ref, remote="origin"):
    """Subject of the tip commit of a remote ref ("Claim #N by ..." or "Release #N by ...")."""
    git("fetch", "-q", remote, f"refs/heads/{ref}")
    return git("log", "-1", "--format=%s", "FETCH_HEAD").stdout.strip()


def changed(ref, remote="origin"):
    """Commit time (Unix seconds) of the tip of a remote ref: the claim, the last beat or the release."""
    git("fetch", "-q", remote, f"refs/heads/{ref}")
    return int(git("log", "-1", "--format=%ct", "FETCH_HEAD").stdout.strip())


def stale(subject_line, last, now, limit=STALE):
    """True when an open claim (not released) had no beat for `limit` seconds."""
    return not subject_line.startswith("Release") and now - last >= limit


def who():
    return git("symbolic-ref", "--short", "HEAD", check=False).stdout.strip() or "unknown"


def push(sha, ref, remote="origin"):
    """True: the remote took the push. False: the ref exists (another run). Exit 2 on any other error."""
    r = git("push", "--porcelain", remote, f"{sha}:refs/heads/{ref}", check=False)
    if r.returncode == 0:
        return True
    if "[rejected]" in r.stdout:                  # not a fast-forward: the ref exists
        return False
    sys.exit(f"git push failed:\n{r.stdout}{r.stderr}")


def claim(number, takeover=False, remote="origin"):
    """Push a new claim commit to the next free slot. Without takeover, the slot is free only when there is
    no claim yet or the last claim was released."""
    found = refs(number, remote)
    top = max(found, default=0)
    if top and not takeover and not subject(slot(number, top), remote).startswith("Release"):
        return None
    msg = f"Claim #{number} by {who()} ({uuid.uuid4().hex})"     # unique: two runs never push the same SHA
    sha = git("commit-tree", EMPTY_TREE, "-m", msg).stdout.strip()
    ref = slot(number, top + 1)
    return ref if push(sha, ref, remote) else None


def release(number, remote="origin", word="Release"):
    """Add a release (or beat) commit on top of the own claim (a fast-forward of the top ref)."""
    found = refs(number, remote)
    if not found:
        return None
    ref = slot(number, max(found))
    if subject(ref, remote).split(" ")[3:4] != [who()]:      # "Claim #N by <branch> (...)", "Beat #N by <branch>"
        sys.exit(f"{ref} belongs to another run: {subject(ref, remote)}")
    sha = git("commit-tree", EMPTY_TREE, "-p", "FETCH_HEAD", "-m", f"{word} #{number} by {who()}").stdout.strip()
    return ref if push(sha, ref, remote) else None


def on_github(remote="origin"):
    """The comment and PR checks need the GitHub API: the tests use a local bare remote."""
    return "github.com" in git("remote", "get-url", remote, check=False).stdout


def api(path):
    from dashboard import api as get                    # gh api in cloud sessions, else GITHUB_TOKEN
    try:
        return get(path)
    except Exception as e:                              # exit 2 like a git error, not 1 ("owned by another run")
        sys.exit(f"GitHub API failed for {path}: {e}")


def started_by_other(comments, me, now, limit=RECENT):
    """Branch of the last "Started by `X`." comment of another branch in the last `limit` seconds, else None."""
    for c in reversed(comments):
        m = re.match(r"Started by `([^`]+)`", c["body"])
        t = datetime.datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")).timestamp()
        if m and m.group(1) != me and now - t < limit:
            return m.group(1)
    return None


def other_pr(pulls, number, me):
    """Number of an open or merged PR of another branch whose body closes ticket `number`, else None."""
    closes = re.compile(rf"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?) #{number}\b", re.I)
    for p in pulls:
        if p["head"]["ref"] != me and (p["state"] == "open" or p.get("merged_at")) and closes.search(p["body"] or ""):
            return p["number"]
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("number", type=int, help="ticket number")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--release", action="store_true", help="give the own claim back")
    g.add_argument("--takeover", action="store_true", help="claim the next slot also when the ticket is owned")
    g.add_argument("--show", action="store_true", help="print the claim refs and their tip commits")
    g.add_argument("--beat", action="store_true", help="show that the own run is alive")
    g.add_argument("--stale", action="store_true", help="exit 0 when the open claim had no beat for 30 minutes")
    g.add_argument("--guard", action="store_true", help="before a push: beat; exit 1 when another branch has a PR")
    ap.add_argument("--remote", default="origin")
    a = ap.parse_args(argv)
    if a.show or a.stale:
        found = refs(a.number, a.remote)
        for k in sorted(found):
            ref = slot(a.number, k)
            age = (time.time() - changed(ref, a.remote)) / 60
            print(ref, subject(ref, a.remote), f"({age:.0f} min ago)")
        if a.stale:
            ref = slot(a.number, max(found)) if found else None
            return 0 if ref and stale(subject(ref, a.remote), changed(ref, a.remote), time.time()) else 1
        return 0
    if a.beat:
        ref = release(a.number, a.remote, word="Beat")
        print(f"beat {ref}" if ref else "nothing to beat")
        return 0
    if a.guard:
        ref = release(a.number, a.remote, word="Beat")      # exits with an error on the claim of another run
        if not ref:
            print(f"no claim of #{a.number}: stop")
            return 1
        pr = on_github(a.remote) and other_pr(api("pulls?state=all&per_page=30"), a.number, who())
        if pr:
            print(f"PR #{pr} of another branch closes #{a.number}: stop and release")
            return 1
        print(f"beat {ref}, no PR of another branch")
        return 0
    if a.release:
        ref = release(a.number, a.remote)
        print(f"released {ref}" if ref else "nothing to release")
        return 0
    if not a.takeover and on_github(a.remote):
        other = started_by_other(api(f"issues/{a.number}/comments?per_page=100"), who(), time.time())
        if other:
            print(f"owned by another run: {other} commented \"Started by\" less than 30 minutes ago")
            return 1
    ref = claim(a.number, a.takeover, a.remote)
    if ref:
        print(f"claimed {ref}")
        return 0
    found = refs(a.number, a.remote)
    print(f"owned by another run: {subject(slot(a.number, max(found)), a.remote) if found else '?'}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
