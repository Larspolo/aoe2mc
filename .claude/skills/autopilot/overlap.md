# Autopilot: runs can overlap

Read this file when a ticket, a branch or a PR of another run is in your way: an old claim, a stalled PR, a takeover
(part of the `autopilot` skill, #1700).

## Claims, stale runs and takeovers

Several runs work at the same time: the owner wants maximum use of the quota. Each run shows that it is alive:
it runs `python3 tools/claim.py N --beat` for its ticket N at least every 20 minutes (after each verify level and
before each push). A usage limit stops all runs at about the same time, and a stopped run never
continues (#231). So a ticket with `in-progress`, and its PR, belong to the other run while
`python3 tools/claim.py N --stale` exits 1, or the ticket, its branch or its PR changed less than 30 minutes ago:
do not touch them. Else the other run stopped: take the ticket over with `python3 tools/claim.py N --takeover`
and say so in a comment. Exit 1 means that another run took it over first: leave it.
A ticket with `in-progress` and no claim ref (older runs): the same rule with the ticket, branch and PR times only.
The workflow `automerge.yml` merges an agent PR when its CI is green (#232, #370). A PR whose CI runs or is green waits
for that workflow: it is not stalled. Exception: a PR with red CI, label `conflict` or a merge conflict, and with no new
commit and no new comment for 30 minutes, is stalled. Take it over at once
(`python3 tools/claim.py N --takeover` with the ticket number N, then comment "Taken over by `<your branch>`: stalled."), for example when its run stopped. Then read the PR comments again: if an older "Taken over by" comment of another branch is less than
30 minutes old, leave the PR to that run. Work on the PR from your session branch (`claim.py` takes the run name
from the current local branch), push with `git push origin HEAD:<branch of the PR>`, and run the guard with
`--pr-branch <branch of the PR>` (#361).
A PR whose ticket has no `in-progress` label is free: any run can fix it (hand-off).
If your usage limit stops you, the next run continues your work through this rule.

