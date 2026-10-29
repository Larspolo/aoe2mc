# Autopilot: improve the process (step 9)

Read this file in step 6.5, before the commit (part of the `autopilot` skill, #1700).

Answer these questions. Do the action for each "yes". Spend little time.
A PR that changes the agent system gets the label `process` (`/issues/N/labels -f "labels[]=process"`, #901): the
dashboard counts them.
- Did something cost you time that one line of text prevents? → a pitfall of one topic (the game program, the replay,
  Paper, the server, records, a design) goes to the end of the "Pitfalls" section of its document (the list in
  `docs/LEARNINGS.md`, "Environment and libraries"); only a line for all runs goes to the end of its section in
  `docs/LEARNINGS.md`: each run loads that file (run 135 moved 16 topic lines out). Do not change other lines
  there, also not to stay below 80 lines: the `improve` skill does that.
- Did a shell command or a code pattern cost you time that a check can find? → add a rule to
  `.claude/hooks/guard-shell.sh` (with a case in `tests/test_guard_shell.py`) or a fast test, not a line of text.
- Was an instruction in `CLAUDE.md` or a skill wrong or missing? → correct it.
- Did you do the same kind of task for the second time? → write a skill for it in `.claude/skills/`.
- Would a test or tool have found a problem earlier? → make a `tooling` ticket (`P1` if it blocks other tickets).
- Did you see a bug outside the ticket? → make a ticket. Do not fix it in this PR.
- Did you write own logic where the platform has a feature for it (CLAUDE.md: the platform features first)? → use the
  feature in this PR when it is small, else make a ticket.
- Did you install a package or download a file by hand? → add it to `scripts/cloud-setup.sh` (raise `SETUP_VERSION`).
- Was a check slow, or CI red, for a reason outside your code (install, download, cache, network)? → fix it
  in this PR when the fix is small, else make a `tooling` ticket.
- Did `git status` show files that do not belong in git (logs, worlds, images, caches)? → add them to `.gitignore`.
- Did something block you that only the owner can change (a host, the environment, the scheduled task, a GitHub
  setting)? → make a `needs-human` ticket with numbered steps and the exact values. Look for an open one first.

After step 8, run `python3 tools/claim.py 0 --review`: exit 0 means that this run does the process review (#898: 200
PRs merged and 4 hours after the last review, 400 or 800 PRs after reviews with no change, #2039, #3465). Then run the `improve` skill.
Run it also when this run failed, or when a ticket took more than 90 minutes. The `improve` skill reviews the whole
system (how runs start, the loop, time and quota, quality, weak spots, reuse, code structure), checks the last change
and the misses (owner tickets for the system), and makes one
change only when a loss is above its threshold (#900). The questions above stay the small check of each ticket. Then run `python3 tools/claim.py 0 --roadmap`: exit 0 means that this run
reviews the feature list of `docs/ROADMAP.md` (the `roadmap` skill, one review per 100 merged PRs).
Do not change a priority that the owner set. Propose it.

