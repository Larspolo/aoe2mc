"""Claim a ticket with a git ref, so that two runs cannot take the same ticket (#211).

A comment or a label never fails when another run was first. A push without force to a new ref fails when the
ref exists, so the ref `claim/N` decides who owns ticket N. The claim commit has no parent and a unique message:
a second push of another claim commit is never a fast-forward. Later claims of the same ticket use
`claim/N-2`, `claim/N-3` ...: the ref with the highest number owns the ticket.

    python3 tools/claim.py N              # claim ticket N; exit 0: yours, exit 1: another run owns it
    python3 tools/claim.py N --release    # give your claim back (needs-human, blocked, hand-off)
    python3 tools/claim.py N --takeover   # take the ticket from a dead run (autopilot "Runs can overlap")
    python3 tools/claim.py N --show       # print the claim refs and the owner

Exit 2: git failed for another reason (network, permission). The workflow `claims.yml` deletes the refs
of a closed ticket: the session proxy gives 403 for branch deletes.
"""
import argparse
import re
import subprocess
import sys
import uuid

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


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


def release(number, remote="origin"):
    """Add a release commit on top of the own claim (a fast-forward of the top ref)."""
    found = refs(number, remote)
    if not found:
        return None
    ref = slot(number, max(found))
    if subject(ref, remote).split(" ")[3:4] != [who()]:      # "Claim #N by <branch> (...)"
        sys.exit(f"{ref} belongs to another run: {subject(ref, remote)}")
    sha = git("commit-tree", EMPTY_TREE, "-p", "FETCH_HEAD", "-m", f"Release #{number} by {who()}").stdout.strip()
    return ref if push(sha, ref, remote) else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("number", type=int, help="ticket number")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--release", action="store_true", help="give the own claim back")
    g.add_argument("--takeover", action="store_true", help="claim the next slot also when the ticket is owned")
    g.add_argument("--show", action="store_true", help="print the claim refs and their tip commits")
    ap.add_argument("--remote", default="origin")
    a = ap.parse_args(argv)
    if a.show:
        for k in sorted(refs(a.number, a.remote)):
            print(slot(a.number, k), subject(slot(a.number, k), a.remote))
        return 0
    if a.release:
        ref = release(a.number, a.remote)
        print(f"released {ref}" if ref else "nothing to release")
        return 0
    ref = claim(a.number, a.takeover, a.remote)
    if ref:
        print(f"claimed {ref}")
        return 0
    found = refs(a.number, a.remote)
    print(f"owned by another run: {subject(slot(a.number, max(found)), a.remote) if found else '?'}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
