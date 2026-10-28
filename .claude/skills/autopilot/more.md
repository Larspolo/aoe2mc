# Autopilot: more tickets in one run

Read this file after step 8 when the argument asks for more than 1 ticket (part of the `autopilot` skill, #1700).

If the argument asks for more than 1 ticket, go back to step 2 after step 8 (finish stalled PRs of other runs, then new owner
feedback, step 3: run `python3 tools/cycle_start.py --last N` again, N = your last ticket: within a priority it puts
the tickets of the same epic or files first, and the code that you read already makes them cheaper). The PRs of this run (on `<session branch>` or `<session branch>-<k>`)
are yours in step 2: when one is red or conflicted, check out its branch (`git fetch origin <b> && git checkout -B <b>
origin/<b>`) and fix it there (`python3 tools/merge_main.py --push N`).

Do each later ticket on a new branch, also while the PR of the last ticket is open: do not wait for that PR (one run
spent 32 calls on such a wait, 2026-10-28). Before the claim of step 5, run `git fetch origin main && git checkout -B
<session branch>-<k> origin/main` (k = 2, 3, ...: one more for each new branch of this run; fetch `main` alone: a fetch
that also names a deleted branch fails as a whole). The scheduled task allows the push to these branches.
`tools/claim.py` names the owner of a claim by the current branch, so claim, beat, guard and push on the new branch.
Push it with `git push -u origin <session branch>-<k>`, and check that the output shows `-> <session branch>-<k>`.
The open PR of the last ticket needs no wait: Automerge merges it when CI is green, and `unconflict.yml` merges `main`
into it. Never force-push: the auto mode denies it ("Git Destructive"; 33 runs lost a step on it on 2026-10-26).
Stop when the context is above 200k tokens (`python3 tools/tokens.py` prints it as `peak`). The window has 1M, but
above 200k each call costs more than 3 times a call of a fresh run (about 65k), so a new run does the next ticket
for less (2026-10-28).

Argument `max`: continue until no ticket is ready, a usage limit stops you, or the context is above 200k tokens.
Do not start other runs: a run of the scheduled task has no `fire_trigger` (#566). The pacer (`pacer.yml`, #3193)
starts the runs that the quota target misses, every 10 minutes. A fresh run has a small context, so it works faster.
