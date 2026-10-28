# Autopilot: merge conflicts

Read this file when a PR has a merge conflict (label `conflict`, or `mergeable_state` is `dirty`), in step 2 or 6.8
(part of the `autopilot` skill, #1700).

A PR with a merge conflict: do the steps below, then continue at step 6.8. Remove the label `conflict` when you push the fix.
The workflow `unconflict.yml` (after each merge and every 20 minutes) merges `origin/main` into a conflicted PR
when git solves the conflict alone (`merge=union` files; `game/data/*.jsonl` by name, key and list item, #2064) or
when both sides only add lines, for example two new entries at one place of a table (`tools/unconflict.py`, #1864),
and starts CI (#280). So a conflict that stays is a real one: Unconflict gives it the label `conflict`.
Locally: `git -c merge.conflictStyle=diff3 merge origin/main`, then `python3 tools/unconflict.py` solves the add-add
hunks (exit 1: it names the real conflict).
In a long session, refresh the copy of the merge driver first (the SessionStart hook copied it at the start, #2096):
`git show origin/main:tools/merge_jsonl.py > "$(git rev-parse --git-common-dir)/merge_jsonl.py"`.

Merge conflict (another PR changed the same lines) → merge `origin/main` into the branch, solve the
conflict, run `ruff check .`, the test files of the conflicted files and of your ticket (not the full fast suite:
the quick CI runs it, `verify` level 1, #1732) and only the `mc` tests of the files of your ticket, and push at
once. Do not run other `mc` tests for a merge: while they run, main moves again and the PR stays without CI
(#604 waited an hour, #669). The quick CI checks the PR, the night CI runs the full suite. A test failure after the
push: fix it in the next push. Do not rebase or force-push a branch that has an open PR.
A conflict in the column "Used today in" of `docs/DESIGN.md`: take main's side (`coverage.yml` writes it).
Two new rows of the feature table at the same place: keep both.
`docs/LEARNINGS.md` has `merge=union`: the merge keeps lines that main removed. `claim.py N --guard` fails
and names them (#563): remove them from the branch, commit, and run the guard again.

## After the push: could a structure have prevented the conflict?

Do this for each conflict that you solved by hand (also a local merge before the first push), after the push.
Spend 5 minutes or less: the ticket stays the main work, and this check must not grow into its own project.
1. Name the hunk: the file, and the table, function or test in it. Find the cause in this list:
   - A generated file or column → generate it on main (`coverage.yml`) or give it a merge driver (`.gitattributes`).
   - Game data in a code literal → a line in a `.jsonl` file with the merge driver `merge=jsonl` (`tools/merge_jsonl.py`).
   - Two new entries at one place that `tools/unconflict.py` did not solve → find why it did not, and teach it that case.
   - A test that asserts a value that changes often (a count, the length of a list, a full list, an exact text)
     → test the behavior or the form of the data, not the value (#1916, #2008).
   - Many tickets append to the end of one file or one list → one file or one line for each item, in sorted order.
   - Two tickets changed the same logic → no structure helps. Better ticket order or smaller tickets can (`queue.md`).
2. Act only when the change is good practice also without this conflict, and fits the direction of the project
   (`docs/PRINCIPLES.md`). Do not add a rule or a structure for one rare conflict.
   - The same cause has an open ticket → add the PR number in one comment there, if it is not there yet.
   - A small fix (one line of `.gitattributes`, a test that asserts too much in the files of your ticket) → do it in
     the next push of this PR, or in your next ticket of the same files.
   - A larger change → a `tooling` ticket (`ticket` skill) with the hunk as the evidence. Look for an open one first.
   - Else → no action.
3. Write one sentence in the `--text` of the run report (`report.md`): `Conflict: <file>, <table or function>;
   cause <cause>; prevent: none | #ticket | PR #n`. The `improve` skill reads these sentences (weak spots).

A push to your own PR branch fails with "fetch first": the workflow Unconflict merged `main` into it (#2120: three
times in 30 minutes while main moved fast). `git fetch origin <branch> && git merge --no-edit origin/<branch>`, run
only the tests of your files, and push at once: the new commits are main's code, and CI tests the merge.
