# Autopilot: more tickets in one run

Read this file after step 8 when the argument asks for more than 1 ticket (part of the `autopilot` skill, #1700).

If the argument asks for more than 1 ticket, go back to step 2 after step 8 (finish stalled PRs of other runs, then read new owner
feedback with `python3 tools/feedback.py`, step 3). In a
cloud session, reset the branch first: `git fetch origin main && git checkout -B <branch> origin/main` (fetch `main` alone:
a fetch that also names a deleted branch fails as a whole, and `origin/main` stays old). Never force-push: the auto mode denies it
("Git Destructive"; 33 runs lost a step on it on 2026-10-26). Push with
`git ls-remote --exit-code --heads origin <branch>` first: exit 2 (the usual case: Automerge deletes the branch after
the merge) → `git push -u origin <branch>`. Exit 0 → `git fetch origin <branch> && git merge --no-edit origin/<branch>`
(its commits are on main already, so the PR diff stays the same), then `git push origin HEAD:<branch>`. A conflict in that merge: take your side (`git checkout --ours FILE`):
main has the squashed old commits, so check that `git diff --stat origin/main` shows only your ticket (#523).
The session branch can carry only one open PR: do the next ticket in a local commit, and push it only when the PR
of the last ticket is merged or closed (`/pulls?head=OWNER:<branch>&state=open` is empty). Else a push replaces
the open PR. While you wait for that merge, beat both claims (the PR's ticket and the local one) at least every 10
minutes: a conflicted PR can wait 45 minutes, and #2713 was taken over as "stuck" with its tested commit still local. After `checkout -B` the upstream is
`origin/main`, so a bare `git push` fails: check that the output shows `-> <branch>`, else the PR has old commits.
Stop when the context is above 200k tokens (`python3 tools/tokens.py` prints it as `peak`). The window has 1M, but
above 200k each call costs more than 3 times a call of a fresh run (about 65k), so a new run does the next ticket
for less (2026-10-28).

Argument `max`: continue until no ticket is ready, a usage limit stops you, or the context is above 200k tokens.
Do not start other runs: a run of the scheduled task has no `fire_trigger` (#566). The pacer session (skill `pacer`)
starts the runs that the quota target misses, every 10 minutes. A fresh run has a small context, so it works faster.
