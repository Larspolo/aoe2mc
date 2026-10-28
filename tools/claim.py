"""Claim a ticket with a git ref, so that two runs cannot take the same ticket (#211).

A comment or a label never fails when another run was first. A push without force to a new ref fails when the
ref exists, so the ref `claim/N` decides who owns ticket N. The claim commit has no parent and a unique message:
a second push of another claim commit is never a fast-forward. Later claims of the same ticket use
`claim/N-2`, `claim/N-3` ...: the ref with the highest number owns the ticket.

    python3 tools/claim.py N              # claim ticket N; exit 0: yours (it adds `in-progress` and "Started by"),
                                          # exit 1: it names the run that was first
    python3 tools/claim.py N --release    # give your claim back (needs-human, blocked, hand-off)
    python3 tools/claim.py N --takeover   # take the ticket from a dead run (stale or released claim, #502)
    python3 tools/claim.py N --show       # print the claim refs and the owner
    python3 tools/claim.py N --beat       # show that the own run is alive (at least every 20 minutes)
    python3 tools/claim.py N --stale      # exit 0: the owner made no claim or beat for 30 minutes (stopped run),
                                          # 10 minutes when its PR has the label `conflict` (#1773)
    python3 tools/claim.py 0 --stuck      # list the `in-progress` tickets of stopped runs (no beat for 30 minutes)
    python3 tools/claim.py N --guard      # before each push: beat, and exit 1 when a PR of another branch closes N
                                          # or a union merge brought back LEARNINGS lines that main removed (#563)
    python3 tools/claim.py N --guard --pr-branch B   # the same, but the open PR of branch B (taken over) is allowed
    python3 tools/claim.py ID --comment   # lock owner comment ID (autopilot step 3); exit 1: another run handles it
    python3 tools/claim.py E --refill     # lock the sub-issues of epic E (0: the whole queue refill, autopilot step 5)
    python3 tools/claim.py 0 --review     # lock the process review after 50 merged PRs (`improve` skill, #898, #2039)
    python3 tools/claim.py 0 --reviewed change   # after the review: "change" or "none" sets the next gap
    python3 tools/claim.py 0 --roadmap    # lock the review of docs/ROADMAP.md after 100 merged PRs (`roadmap` skill)

Two runs did one ticket (#288): one commented "Started by" and worked without the claim ref. So a claim also fails
when another branch commented "Started by" in the last 30 minutes or has an active PR for the ticket (#491), and `--guard` stops a run before its push when it does not own the claim or another branch has a PR for the ticket. The GitHub checks run only for a GitHub remote.

A usage limit stops all runs at about the same time, and a stopped run never continues (#231). Its last beat is
before the stop, so its ticket is stale at most 30 minutes after the limit resets. A live run beats again.

Three runs read one owner comment at the same time and made three copies of one epic (#320). So a run locks a
comment before it acts on it: `--comment` pushes `claim/comment-ID` once (no slots, no release).
Three runs refilled the queue of one epic within 2 minutes and made copies of tickets (#505). So a run locks the
refill before it makes tickets: `--refill` pushes `claim/refill-E-S` once. S is the state of the work: the number of
closed sub-issues of epic E (a new lock when a sub-issue closes), or the UTC hour for E = 0 (the whole refill) and for
a ticket E with no sub-issue (#855).

Parallel runs read the same `runs` counter of the status issue, so "every 5th run" lost 7 of 10 process reviews
(#898). So `--review` locks one review: `claim/review-<gap>pr-<last review>-<k>`, and only when `gap` PRs merged after
the last review (`last_review` in the state comment of #1). A review with no change doubles the gap (50, 100, 200
merged PRs), a change sets it back to 50 (`--reviewed`). `--roadmap` locks the roadmap review the same way, 100 merged
PRs after `last_roadmap`. A gap counts merged PRs, not minutes: the speed of the project changes (#2039). The other
times of this tool stay in seconds: a run that stopped merges nothing, so only the clock finds it.

Exit 2: git failed for another reason (network, permission). The workflow `claims.yml` deletes the refs
of a closed ticket: the session proxy gives 403 for branch deletes.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
import time
import uuid

from agent_config import CONFIG

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
REVIEW, REVIEW_MAX = 50, 200    # merged PRs: the first and the longest gap of the process review (#898, #1697, #2039)
ROADMAP = 100               # merged PRs between two reviews of docs/ROADMAP.md (#2039)
STATUS = CONFIG["status"]["issue"]   # the status issue: its state comment holds the last reviews
# The times below find a run that stopped: a stopped run merges nothing, so they stay on the clock (#2039).
STALE = 30 * 60             # seconds without a claim or beat: the run stopped (usage limit, crash)
RECENT = 30 * 60            # seconds: a "Started by" comment of another branch owns the ticket for this time (#288)
CONFLICT = 10 * 60          # seconds: the stale time of a ticket whose PR has the label `conflict` (#1773)


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


def owner(subject_line):
    """The branch of a claim, beat or release line ("Claim #N by <branch> (...)"), in backticks."""
    words = subject_line.split(" ")
    return f"`{words[3]}`" if len(words) > 3 else "another run"


def first(number, remote="origin"):
    """The run that holds ticket `number` and its last sign of life: the text of a lost claim."""
    found = refs(number, remote)
    if not found:
        return "another run"
    ref = slot(number, max(found))
    line = subject(ref, remote)
    return f"{owner(line)} (its last {line.split(' ')[0].lower()} {(time.time() - changed(ref, remote)) / 60:.0f} min ago)"


def start(number):
    """Add `in-progress` and the comment "Started by `<branch>`." after a won claim. A run that commented by hand
    without the claim worked on one ticket with another run (#288, #1749), so only the claim writes them."""
    from dashboard import FOOTER, api as call
    try:
        call(f"issues/{number}/labels", "POST", {"labels": ["in-progress"]})
        call(f"issues/{number}/comments", "POST", {"body": f"Started by `{who()}`.{FOOTER}"})
        print(f"added in-progress and \"Started by `{who()}`.\" to #{number}")
    except Exception as e:                              # the claim ref is the lock: the ticket is yours anyway
        print(f"the claim is yours, but the label or the comment failed ({e}): add them by hand")


def stale(subject_line, last, now, limit=STALE):
    """True when an open claim (not released) had no beat for `limit` seconds."""
    return not subject_line.startswith("Release") and now - last >= limit


def who():
    return git("symbolic-ref", "--short", "HEAD", check=False).stdout.strip() or "unknown"


def lane():
    """" lane NAME" when the run set `git config aoe2mc.lane NAME` (a Haiku run, #1727), else "": the pacer
    counts the runs of each lane (`health.lane_claims`)."""
    name = git("config", "--get", "aoe2mc.lane", check=False).stdout.strip()
    return f" lane {name}" if name else ""


def deep_lane():
    """True when this run may do the process review, the roadmap review and the queue refill: always, but only the
    runs of the deep lane while `reserved` in `[pacing]` of agent.toml names `deep` (owner, 2026-10-28): the main runs
    work at low effort, and these steps steer many later tickets."""
    return "deep" not in CONFIG.get("pacing", {}).get("reserved", ()) or lane() == " lane deep"


def push(sha, ref, remote="origin"):
    """True: the remote took the push. False: the ref exists (another run). Exit 2 on any other error."""
    r = git("push", "--porcelain", remote, f"{sha}:refs/heads/{ref}", check=False)
    if r.returncode == 0:
        return True
    if "[rejected]" in r.stdout:                  # not a fast-forward: the ref exists
        return False
    sys.exit(f"git push failed:\n{r.stdout}{r.stderr}")


def claim(number, takeover=False, remote="origin", limit=STALE):
    """Push a new claim commit to the next free slot. The slot is free only when there is no claim yet or the
    last claim was released. A takeover also takes a stale claim, but never a live one: three runs took over
    one hand-off in 15 seconds, and each pushed the next slot (#502)."""
    found = refs(number, remote)
    top = max(found, default=0)
    if top:
        line = subject(slot(number, top), remote)
        if not line.startswith("Release") and not (takeover and stale(line, changed(slot(number, top), remote),
                                                                     time.time(), limit)):
            return None
    msg = f"Claim #{number} by {who()} ({uuid.uuid4().hex}){lane()}"   # unique: two runs never push the same SHA
    sha = git("commit-tree", EMPTY_TREE, "-m", msg).stdout.strip()
    ref = slot(number, top + 1)
    return ref if push(sha, ref, remote) else None


def claim_comment(cid, remote="origin"):
    """Lock comment `cid`: True when this run pushed `claim/comment-ID` first."""
    sha = git("commit-tree", EMPTY_TREE, "-m", f"Claim comment {cid} by {who()} ({uuid.uuid4().hex})").stdout.strip()
    return push(sha, f"claim/comment-{cid}", remote)


def refill_state(epic, remote="origin", now=None):
    """The state part of the refill lock: closed sub-issues of the epic on GitHub, else the UTC hour and its 10-minute
    slot: the runs close about 25 tickets per hour, so one refill per hour, then per 15 minutes, left the queue empty
    (#609, #650). A ticket with no sub-issue gets the slot too: else the lock of a run that did not split it stays
    for ever (#855: #397 waited 5 hours)."""
    t = datetime.datetime.fromtimestamp(now or time.time(), datetime.timezone.utc)
    slot = t.strftime("%Y%m%d%H") + str(t.minute // 10)
    if epic and on_github(remote):
        s = api(f"issues/{epic}").get("sub_issues_summary") or {}
        return str(s.get("completed", 0)) if s.get("total") else "0-" + slot
    return slot


def claim_refill(epic, state, remote="origin"):
    """Lock the refill of epic `epic` in state `state`: True when this run pushed `claim/refill-E-S` first."""
    msg = f"Claim refill {epic}-{state} by {who()} ({uuid.uuid4().hex})"
    return push(git("commit-tree", EMPTY_TREE, "-m", msg).stdout.strip(), f"claim/refill-{epic}-{state}", remote)


def agent_state(body):
    """The JSON of the state comment `<!-- agent-state: {...} -->` of the status issue, or {}."""
    m = re.search(r"<!-- agent-state: (\{.*?\}) -->", body or "")
    return json.loads(m[1]) if m else {}


def pr_slot(last, gap, merged):
    """The lock key of a review that waits for `gap` merged PRs after the time `last` (ISO, or None: no review yet), or
    None when fewer PRs merged since then. merged: the PRs merged after `last`. The key holds `last` and the number of
    full gaps: one run takes each review, and a review that a run did not finish opens again one gap later."""
    if merged < gap:
        return None
    return f"{gap}pr-{re.sub(r'[^0-9TZ]', '', last or '') or 'none'}-{merged // gap}"


def merged_since(last, gap, remote="origin"):
    """The number of PRs merged after the ISO time `last`. With no last review, or without GitHub (the tests): `gap`,
    so the review starts."""
    if not last or not on_github(remote):
        return gap
    from dashboard import merges
    try:
        return len(merges(since=datetime.datetime.fromisoformat(last.replace("Z", "+00:00"))))
    except Exception as e:                              # exit 2 like a git error, not 1 ("another run does it")
        sys.exit(f"GitHub API failed for the merged PRs: {e}")


def utc(now=None):
    return datetime.datetime.fromtimestamp(now or time.time(), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def with_state(body, state):
    """The body of the status issue with `state` in its state comment."""
    new = f"<!-- agent-state: {json.dumps(state)} -->"
    old = re.search(r"<!-- agent-state: \{.*?\} -->", body or "")
    return body.replace(old[0], new) if old else new + "\n" + (body or "")


def reviewed(body, changed, now=None):
    """The body of the status issue after a review: a change sets the gap back to REVIEW merged PRs, no change doubles
    it (at most REVIEW_MAX). The other keys of the state comment stay; `review_minutes` (the time slot before #2039)
    goes."""
    state = {k: v for k, v in agent_state(body).items() if k != "review_minutes"}
    gap = REVIEW if changed else min(2 * state.get("review_prs", REVIEW), REVIEW_MAX)
    return with_state(body, {**state, "last_review": utc(now), "review_prs": gap})


def claim_lock(kind, key, remote="origin"):
    """Push `claim/<kind>-<key>` once: True when this run was first."""
    msg = f"Claim {kind} {key} by {who()} ({uuid.uuid4().hex})"
    return push(git("commit-tree", EMPTY_TREE, "-m", msg).stdout.strip(), f"claim/{kind}-{key}", remote)


def release(number, remote="origin", word="Release"):
    """Add a release (or beat) commit on top of the own claim (a fast-forward of the top ref)."""
    found = refs(number, remote)
    if not found:
        return None
    ref = slot(number, max(found))
    line = subject(ref, remote)
    if line.split(" ")[3:4] != [who()]:                      # "Claim #N by <branch> (...)", "Beat #N by <branch>"
        sys.exit(f"{ref} belongs to another run: {owner(line)} took #{number} over ({line}). Stop the work on #{number}"
                 f" now: no push, no comment, no release; pick the next ticket.")
    sha = git("commit-tree", EMPTY_TREE, "-p", "FETCH_HEAD", "-m", f"{word} #{number} by {who()}{lane()}").stdout.strip()
    return ref if push(sha, ref, remote) else None


def revived(path=CONFIG["docs"]["learnings"], base=f"origin/{CONFIG['branch']}"):
    """Lines of `path` that a `merge=union` merge of `base` brought back after `base` removed them (#563).

    M is the last merged state of `base` (the merge base). A line of HEAD that is not in M and that no own commit
    after M added came from an older version through the union merge."""
    m = git("merge-base", "HEAD", base, check=False).stdout.strip()
    if not m:
        return []
    old = set(git("show", f"{m}:{path}", check=False).stdout.splitlines())
    own = {line[1:] for line in git("log", "-p", "--no-merges", "--format=", f"{m}..HEAD", "--", path).stdout.splitlines()
           if line.startswith("+") and not line.startswith("+++")}
    head = git("show", f"HEAD:{path}", check=False).stdout.splitlines()
    return [line for line in head if line.strip() and line not in old and line not in own]


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


def closes(number):
    return re.compile(rf"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?) #{number}\b", re.I)


def prose(body):
    """The PR body without code blocks and code spans: GitHub closes no issue from a keyword in code (#536)."""
    return re.sub(r"```.*?(```|$)|`[^`\n]*`", "", body or "", flags=re.S)


def other_pr(pulls, number, me, taken=None):
    """Number of an open or merged PR of another branch whose body closes ticket `number`, else None.
    taken: the branch of a PR that this run took over (#361): its open PR is the run's own."""
    closes_n = closes(number)
    for p in pulls:
        own = p["head"]["ref"] == me or p["head"]["ref"] == taken and p["state"] == "open"
        if not own and (p["state"] == "open" or p.get("merged_at")) and closes_n.search(prose(p["body"])):
            return p["number"]
    return None


def active_pr(pulls, number, me, now, limit=RECENT):
    """Number of an open PR of another branch that closes ticket `number` and changed in the last `limit` seconds,
    else None (#491): its run still works on it. A stalled PR does not count, so a takeover stays possible."""
    for p in pulls:
        t = datetime.datetime.fromisoformat(p["updated_at"].replace("Z", "+00:00")).timestamp()
        if p["head"]["ref"] != me and p["state"] == "open" and now - t < limit and closes(number).search(prose(p["body"])):
            return p["number"]
    return None


def conflict_pr(pulls, number, now, pushed, limit=CONFLICT):
    """Number of an open PR that closes ticket `number`, has the label `conflict` (Automerge could not merge it) and
    no new commit for `limit` seconds, else None. pushed(p): the Unix time of its head commit. Its run reported and
    went on to the next ticket, so its claim has no beat: 9 of 12 takeovers in 24 hours waited 30 minutes (#1773)."""
    for p in pulls:
        if p["state"] == "open" and "conflict" in [x["name"] for x in p.get("labels", [])] \
                and closes(number).search(prose(p["body"])) and now - pushed(p) >= limit:
            return p["number"]
    return None


def head_time(p):
    t = api(f"commits/{p['head']['sha']}")["commit"]["committer"]["date"]
    return datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()


def stuck(tickets, tips, now, limit=STALE):
    """[(number, reason)] of the `in-progress` tickets whose run stopped: the claim had no beat for `limit` seconds,
    the run released it and left the label, or the ticket has no claim ref and no change for `limit` seconds.
    tickets: {number: Unix time of the last change}; tips: {number: (subject, Unix time) of its highest slot}.
    Only the claim decides, not the PR: Unconflict and Automerge merge main into the PR of a stopped run and
    comment on it, so #2160 and #2228 looked alive for 6 hours with red CI, and #2049 had no PR to find."""
    out = []
    for n, changed_at in sorted(tickets.items()):
        line, t = tips.get(n, (None, changed_at))
        if now - t >= limit and (line is None or line.startswith("Release") or stale(line, t, now, limit)):
            out.append((n, f"{(line or 'no claim').split(' by ')[0]}, {(now - t) / 60:.0f} min ago"))
    return out


def tips(remote="origin"):
    """{ticket: (subject, Unix time)} of the highest claim slot of each ticket, with one ls-remote and one fetch."""
    top = {}
    for line in git("ls-remote", remote, "refs/heads/claim/*").stdout.splitlines():
        sha, ref = line.split("\t")
        m = re.fullmatch(r"refs/heads/claim/(\d+)(?:-(\d+))?", ref)
        if m and int(m.group(2) or 1) >= top.get(int(m.group(1)), (0, ""))[0]:
            top[int(m.group(1))] = (int(m.group(2) or 1), sha)
    if top:
        git("fetch", "-q", remote, *[f"refs/heads/{slot(n, k)}" for n, (k, _) in top.items()])
    out = {}
    for n, (_, sha) in top.items():
        t, _, line = git("log", "-1", "--format=%ct %s", sha).stdout.strip().partition(" ")
        out[n] = (line, int(t))
    return out


def stale_limit(number, remote="origin"):
    """CONFLICT seconds when a PR of ticket `number` waits on a merge conflict (`conflict_pr`), else STALE."""
    if not on_github(remote):
        return STALE
    pr = conflict_pr(api("pulls?state=open&per_page=100"), number, time.time(), head_time)
    return CONFLICT if pr else STALE


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("number", type=int, help="ticket number (--comment: the comment ID, --refill: the epic)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--release", action="store_true", help="give the own claim back")
    g.add_argument("--takeover", action="store_true", help="claim the next slot also when the open claim is stale")
    g.add_argument("--show", action="store_true", help="print the claim refs and their tip commits")
    g.add_argument("--beat", action="store_true", help="show that the own run is alive")
    g.add_argument("--stale", action="store_true", help="exit 0 when the open claim had no beat for 30 "
                   "minutes (10 when its PR has the label `conflict` and no new commit for 10 minutes)")
    g.add_argument("--stuck", action="store_true", help="list the in-progress tickets of stopped runs (number 0); "
                   "exit 1: none")
    g.add_argument("--guard", action="store_true", help="before a push: beat; exit 1 when another branch has a PR")
    g.add_argument("--comment", action="store_true", help="lock the owner comment with this ID")
    g.add_argument("--refill", action="store_true", help="lock the new sub-issues of this epic (0: the whole refill)")
    g.add_argument("--review", action="store_true", help="lock the process review after its gap of merged PRs (number 0)")
    g.add_argument("--reviewed", choices=("change", "none"), help="after the review: set the next gap")
    g.add_argument("--roadmap", action="store_true", help="lock the roadmap review after 100 merged PRs (number 0)")
    ap.add_argument("--state", help="--refill: the state part of the lock (default: closed sub-issues, or the hour)")
    ap.add_argument("--pr-branch", metavar="BRANCH", help="--guard: the branch of a PR that this run took over")
    ap.add_argument("--remote", default="origin")
    a = ap.parse_args(argv)
    if a.comment:
        if claim_comment(a.number, a.remote):
            print(f"claimed comment {a.number}")
            return 0
        print(f"comment {a.number}: another run handles it")
        return 1
    if (a.review or a.roadmap or a.refill) and not deep_lane():
        print(f"the deep lane does the {'process review' if a.review else 'roadmap review' if a.roadmap else 'queue refill'}"
              " (`reserved` in agent.toml names `deep`): skip it")
        return 1
    if a.review or a.roadmap:
        body = api(f"issues/{STATUS}")["body"] if on_github(a.remote) else ""
        state, kind = agent_state(body), "review" if a.review else "roadmap"
        last, gap = (state.get("last_review"), state.get("review_prs", REVIEW)) if a.review else \
            (state.get("last_roadmap"), ROADMAP)
        key = pr_slot(last, gap, merged_since(last, gap, a.remote))
        if key and claim_lock(kind, key, a.remote):
            if a.roadmap and on_github(a.remote):         # the roadmap skill has no end step: count from its start
                from dashboard import api as call
                body = api(f"issues/{STATUS}")["body"]    # read again: other runs and the dashboard change it too
                call(f"issues/{STATUS}", "PATCH", {"body": with_state(body, {**agent_state(body), "last_roadmap": utc()})})
            print(f"claimed {kind} {key}")
            return 0
        print(f"no {kind} now: fewer than {gap} PRs merged since the last one, or another run does it")
        return 1
    if a.reviewed:
        from dashboard import api as call
        body = reviewed(api(f"issues/{STATUS}")["body"], a.reviewed == "change")
        call(f"issues/{STATUS}", "PATCH", {"body": body})
        print(agent_state(body))
        return 0
    if a.refill:
        state = a.state or refill_state(a.number, a.remote)
        key = f"{a.number}-{state}"
        if claim_refill(a.number, state, a.remote):
            print(f"claimed refill {key}")
            return 0
        print(f"refill {key}: another run makes the tickets")
        return 1
    if a.stuck:
        issues = api("issues?state=open&labels=in-progress&per_page=100")
        tickets = {i["number"]: datetime.datetime.fromisoformat(i["updated_at"].replace("Z", "+00:00")).timestamp()
                   for i in issues if "pull_request" not in i}
        pulls = api("pulls?state=open&per_page=100")
        found = stuck(tickets, tips(a.remote), time.time())
        for n, reason in found:
            pr = next((p["number"] for p in pulls if closes(n).search(prose(p["body"]))), None)
            print(f"#{n} {f'PR #{pr}' if pr else 'no PR'}: {reason}")
        return 0 if found else 1
    if a.show or a.stale:
        found = refs(a.number, a.remote)
        for k in sorted(found):
            ref = slot(a.number, k)
            age = (time.time() - changed(ref, a.remote)) / 60
            print(ref, subject(ref, a.remote), f"({age:.0f} min ago)")
        if a.stale:
            ref = slot(a.number, max(found)) if found else None
            return 0 if ref and stale(subject(ref, a.remote), changed(ref, a.remote), time.time(),
                                      stale_limit(a.number, a.remote)) else 1
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
        back = revived(base=f"{a.remote}/main")
        if back:
            print(f"docs/LEARNINGS.md keeps {len(back)} lines that main removed (union merge, #563): remove them")
            print("\n".join(back))
            return 1
        pr = on_github(a.remote) and other_pr(api("pulls?state=all&per_page=30"), a.number, who(), a.pr_branch)
        if pr:
            print(f"PR #{pr} of another branch closes #{a.number}: stop and release")
            return 1
        print(f"beat {ref}, no PR of another branch")
        return 0
    if a.release:
        ref = release(a.number, a.remote)
        print(f"released {ref}" if ref else "nothing to release")
        return 0
    issue = api(f"issues/{a.number}") if on_github(a.remote) else None
    if isinstance(issue, dict) and issue.get("state") == "closed":   # the candidate list was older (#2339)
        print(f"#{a.number} is closed: pick the next candidate")
        return 1
    if not a.takeover and on_github(a.remote):
        other = started_by_other(api(f"issues/{a.number}/comments?per_page=100"), who(), time.time())
        if other:
            print(f"owned by another run: `{other}` was first (\"Started by\" less than 30 minutes ago). Pick the next"
                  " candidate, do not comment.")
            return 1
        pulls = api("pulls?state=open&per_page=100")
        pr = active_pr(pulls, a.number, who(), time.time())
        if pr:
            print(f"owned by another run: its PR #{pr} closes #{a.number} and changed less than 30 minutes ago. Pick the"
                  " next candidate, do not comment.")
            return 1
    ref = claim(a.number, a.takeover, a.remote, stale_limit(a.number, a.remote) if a.takeover else STALE)
    if ref:
        print(f"claimed {ref}")
        if on_github(a.remote) and not a.takeover:
            start(a.number)
        return 0
    print(f"owned by another run: {first(a.number, a.remote)} was first. Pick the next candidate, do not comment.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
