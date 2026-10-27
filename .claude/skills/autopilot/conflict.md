# Autopilot: merge conflicts

Read this file when a PR has a merge conflict (label `conflict`, or `mergeable_state` is `dirty`), in step 2 or 6.8
(part of the `autopilot` skill, #1700).

A PR with a merge conflict: do the steps below, then continue at step 6.8. Remove the label `conflict` when you push the fix.
The workflow `unconflict.yml` (after each merge and every 20 minutes) merges `origin/main` into a conflicted PR
when git solves the conflict alone (`merge=union` files) or when both sides only add lines, for example two new
entries at one place of a table (`tools/unconflict.py`, #1864), and starts CI (#280). So a conflict that stays is a real one.
Locally: `git -c merge.conflictStyle=diff3 merge origin/main`, then `python3 tools/unconflict.py` solves the add-add
hunks (exit 1: it names the real conflict).

Merge conflict (another PR changed the same lines) → merge `origin/main` into the branch, solve the
conflict, run `ruff check .`, the fast tests and only the `mc` tests of the files of your ticket, and push at
once. Do not run other `mc` tests for a merge: while they run, main moves again and the PR stays without CI
(#604 waited an hour, #669). The quick CI checks the PR, the night CI runs the full suite. A test failure after the
push: fix it in the next push. Do not rebase or force-push a branch that has an open PR.
A conflict in the column "Used today in" of `docs/DESIGN.md`: take main's side (`coverage.yml` writes it).
Two new rows of the feature table at the same place: keep both.
`docs/LEARNINGS.md` has `merge=union`: the merge keeps lines that main removed. `claim.py N --guard` fails
and names them (#563): remove them from the branch, commit, and run the guard again.
