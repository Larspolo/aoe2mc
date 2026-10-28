---
name: improve
description: Review how efficiently the agent works on aoe2mc and make one concrete improvement to the whole system (CLAUDE.md, skills, tools, tests, CI workflows, the cloud setup script, settings). Use when `python3 tools/claim.py 0 --review` gives the review slot to the run (autopilot step 9), after a run that failed or took more than 90 minutes, or when the owner asks for a process review.
---

# Improve the process

The aim: more closed tickets for the same usage, with the same quality. Look at the whole system, not only
the skills: the agent process, CI, the cloud environment, the repository and the scheduling of the runs.
Make at most one improvement per review, only where it pays, and stop changing things when the system is efficient
(owner, #900: "only where it makes sense ... in the broadest sense"). The main number is the release progress per
quota (`tools/health.py`, #899): the game goals 1 to 3 of `docs/ROADMAP.md`. Goal 4 of that file is this system.

**The limit is the usage limit** (owner, 2026-10-27). The 7-day and the 5-hour window of the subscription limit the
number of runs, not the run minutes. So the main cost of a loss is quota, and minutes come second. Which part of
the system uses the quota best or worst is not known: find the bottleneck from data, do not assume it. The owner
thinks that tokens per run can be one (`tools/tokens.py`, the `Tokens:` lines), but that is a hunch to test, not a
fact. When the data cannot name the bottleneck, the first ticket expands the data (step 2). Each bottleneck and each
data gap gets its own ticket on the board (step 3), so that the owner sees the work on it.

## 0. Check the last change

Read the newest line of "Process changes" on the status issue that has `before:` numbers: a line of a review or of a
ticket run (autopilot step 8, #1738); skip `before: -` (a pitfall line). Compute the same numbers now (step 1).
Did they get better?
- Yes, or too early to say (less than 10 Metrics lines since the change) → keep it. Say so in the report.
- No → undo it or try another way to fix the same loss. This is the change of this review. Say so in the report.

**Misses** (#1909). The line `Misses` of `tools/health.py` lists the issues that the owner opened to change the system
(labels `process`, `tooling`, `cleanup`). Each one is a change that this loop did not find. An owner comment on a
process ticket that asks for a wider fix is a miss too (#1702: "Should we generalise this further?"). For each miss
without a line `miss #N` in "Process changes": find the signal that would have found it (a number of
`tools/health.py`, a check in CI, an area of step 2), and add that signal. A miss comes before the largest loss of
step 2: it is the change of this review. Report it as `- <date>: miss #N: <the new signal> (PR #n)`.

## 1. Collect the data

Run `python3 tools/health.py --prs 50 --compare` first (about 2 minutes, #1697): it prints the last 50 merged PRs and,
under each line that differs, the 50 PRs before (`  before: ...`). A window of merged PRs keeps its size when the speed
of the project changes; a window of hours does not (50 PRs were 1.7 hours on 2026-10-27, #1909). A change of more than
20 % between the two periods (the quota per merged PR, the tokens per run, the phase minutes, the takeovers) is a
finding. Use `--hours 24` for the slow numbers (night runs, reopened tickets). It prints the CI runs per workflow,
the slowest CI steps, the setup minutes, takeovers, releases, merge conflicts (and their files), the minutes of each
phase, the quota per merged PR, the release points per 1 % of 7-day quota (the main number: progress to the goals per
quota), the tokens per run and per merged PR and the largest token sinks (from the `Tokens:` lines), weak spots (rework, bugs of check tickets, red night runs), claim-to-merge minutes and files that do not belong in git. Collect by hand only what it does not print.

- Tokens: `python3 tools/tokens.py --top 15` on this run (the sinks one by one: which file, which command). The
  `Tokens:` lines of `tools/health.py` give only the groups. The token counts are estimates (API price ratios, about
  4 characters per token): compare them with the rise of the `Usage:` lines before you trust them.
- Verify: `tools/health.py` "Verify commands" sums the `verify` fields of the `Tokens:` lines (the minutes and the count
  of `pytest`, `pytest -m mc`, `ruff`, `mc_shot.py`, the wait loops ...; `python3 tools/tokens.py --verify` for one run, #1704).
- Agent: the last 20 run comments by the agent on the status issue (label `agent-status`). Each has a line
  `Metrics: ticket #n · size · result · minutes · setup m min · checks k · checks c min · time sinks: ...`.
  Also the tickets and PRs closed in that period, and rework (tickets that the owner reopened, or that came
  from owner feedback on merged work).
- CI: the last 50 runs of each workflow (`/actions/runs?per_page=50`: `conclusion`, `run_started_at`,
  `updated_at`) and the step times of slow runs (`/actions/runs/ID/jobs`). Read the log of a failed job
  (`mcp__github__get_job_logs`) when the cause is not in the code: install, download, cache, network, runner.
- Environment: the `setup` minutes and the time sinks with "install", "download", "blocked" or "denied".
  The SessionStart hook prints a line when the setup script of the environment is older than `scripts/cloud-setup.sh`.
- Repository: `git ls-files` for files that do not belong in git (logs, worlds, images over 1 MB, caches).
- Scheduling: "Taken over", "Released" and claim comments, stalled PRs, merge conflicts per PR, and the time
  from the claim to the merge.
- `docs/LEARNINGS.md` and the "Process changes" list on the status issue (what was tried before).
- Decisions: the share of `taken` in the lines of `docs/DECISIONS.md` that have a recommendation (2026-10-27: 9 of 19,
  47 %), and the lines with `new` or an exception. When the share of the last 10 is lower than the one before, or 3 lines
  have `new`, the principles do not predict the owner: update `docs/PRINCIPLES.md` (a new principle or a sharper rule,
  with the decisions as evidence) in this review, and list the change on the status issue.

## 2. Find the largest loss

Go through the seven areas. For each one, note its largest loss in quota (share of the 5-hour and 7-day usage), else in
minutes of run time (or tickets) per day:

1. **How runs start:** the scheduled task prompt, the pacer (`tools/usage.py`, `tools/pacer.py`, `pacer.yml`), the quota
   target, idle runs (no ticket ready, stopped at once), runs that hit the usage limit.
2. **The loop:** the steps of `.claude/skills/autopilot` and the phase minutes of the `Metrics:` lines
   (`read`, `claim`, `code`, `verify`, `ci`, `conflict`, `report`); steps that cost time and change nothing.
3. **Quota:** the quota per merged ticket, the release progress per quota, the quota of work that gives no merge
   (idle runs, closed PRs, rework), the quota of the sessions that are not runs, the
   token sinks (`Tokens:` lines). The phase shares in minutes come second.
4. **Quality:** rework (owner corrections, reopened tickets, follow-ups of merged work), bugs found by check tickets,
   red night CI runs.
5. **Weak spots:** merge conflicts (and the `Conflict:` sentences of the run reports: causes that come again need a structure, `autopilot/conflict.md`), takeovers (`tools/health.py --takeovers`: the cause of each, #1703), refused commands, slow tests, tools missing in the environment.
6. **Reuse:** what is aoe2mc-specific in the skills, tools and workflows, and how hard it is to set it up for
   another project (epic #909).
7. **Code structure** (#1909): how easy the code is to change. The line `Data in the code` of `tools/health.py`
   (the list `[lint] data` of `agent.toml`: it must go down, and each place in it needs an open sub-issue of the data
   epic), the tables and functions in the conflict hunks (not only the files), tests that copy the values or the
   length of a data file (#2008), the largest files and functions, and the rules in `CLAUDE.md` that only prevent a
   mistake. The good practices: one place for each fact, domain data in data files, tests that check behavior, no
   dead code.

**Is the data enough?** The bottleneck is clear only when one loss is larger than the others by numbers of the same
kind (quota, or minutes), measured over at least 10 runs. When it is not clear (no number for an area, two losses of
the same size, a number that does not match the `Usage:` rise, or a cause that you only guess), the bottleneck of
this review is the data gap: the change adds the measurement that answers it (a field of the `Metrics:` or `Tokens:`
line, a number in `tools/health.py`, a finer label in `tools/tokens.py`). Write the question that the new data must
answer, for example "Which part of the 7-day quota goes to runs that merge nothing?".

The threshold: change something only when the largest loss is above about 5 % of the quota or of the run minutes of
the period, or one ticket per day, or a quality problem that a person would see. Else make no change ("no change" in step 5).
A loss that comes back counts with its full cost: its minutes and quota, the takeovers that it causes, and the rule
lines that it added to `CLAUDE.md` and `docs/LEARNINGS.md` (each run loads them in each turn). The table conflicts were
4 % of the minutes in 24 hours, below the threshold, but the same 24 hours had 14 takeovers, and `CLAUDE.md` had 4 rules
against them (#1702, #1909).

Compute the numbers of all areas: tickets per run, median minutes for `size:S` and `size:M` tickets
(last 5 runs against the 5 runs before), setup minutes, verify rounds per PR, CI rounds per PR, the minutes from the PR
to the merge (CI and Automerge), CI failures that are not in the code, rework, takeovers and conflicts.
The repository is public: Actions minutes are free, but at most 20 jobs run at the same time.
Then find the one pattern that costs the most. Typical
patterns and their fixes:

| Area | Pattern | Fix |
|---|---|---|
| Agent | Much reading to find code | Better code map in `CLAUDE.md`, or a short `docs/architecture.md` |
| Agent | The same manual check again and again | A tool in `tools/` or a test fixture |
| Agent | The same kind of ticket again (for example a new building design) | A dedicated skill in `.claude/skills/` |
| Agent | Unclear tickets, many questions | A better form in the `ticket` skill, ask earlier |
| Agent | Rework after owner feedback | A rule from the feedback in `CLAUDE.md` |
| Agent | Runs longer than 90 minutes | Stricter size rules, split earlier |
| CI | The night run (full suite) red after green PRs | A check in the `verify` skill that finds it before the push, or fix the flaky test |
| CI | PRs wait for CI in the queue (20 jobs at the same time) | Fewer event runs (`concurrency`), or split a slow job |
| CI | A slow step (install, download) | `actions/cache` with the correct path and key, or a smaller install |
| CI | A cache that is never restored ("Cache not found") | Correct the cache path or key |
| CI | Slow tests | Faster fixtures, or move a test to the slow suite |
| Environment | Runs install or download the same thing | Add it to `scripts/cloud-setup.sh` |
| Environment | `setup` more than 3 minutes | Move work from the SessionStart hook to the setup script |
| Environment | A blocked host, a missing variable | `needs-human` ticket with the exact host or name |
| Repository | Files in git that do not belong there | `.gitignore`, and a test that fails on such files |
| Scheduling | Dead claims, stalled PRs | Better claim or takeover rules (`tools/claim.py`, autopilot) |
| Scheduling | Merge conflicts in generated files | A merge driver in `.gitattributes`, or generate the file in CI |
| Scheduling | Merge conflicts in hand-written tables | Move all tables of that kind to `merge=union` data files, not only the table of the conflict |
| Code | Domain data in the code (`Data in the code`) | A sub-issue of the data epic for each place |
| Code | Tests that copy the values or the length of a data file | A form test of the data file (#1916, #2008) |
| Code | A rule in `CLAUDE.md` that only prevents a mistake ("each entry on its own line") | A check or a structure that makes the rule unnecessary; then remove the rule |
| Scheduling | Runs stop because no ticket is ready | Split epics earlier |
| Data | The data cannot name the largest loss | Add the measurement first (above, "Is the data enough?") |
| Tokens | Sink `base` large (each call reads it again) | The `repo` part: shorter `CLAUDE.md` and `LEARNINGS.md`, topic lines to the docs that load only when needed. The rest (system prompt, tool definitions of the connectors): a `needs-human` ticket to turn off connectors that runs do not use |
| Tokens | Sink `Read` or `Bash cat`/`sed` of large files | Better code map, `Grep` and line ranges, a smaller file |
| Tokens | Sink `Bash pytest` or another long command output | `-q`, `\| tail -N`, a tool option for a short summary |
| Tokens | Sink `mcp ...` or `Bash gh` (JSON of the GitHub API) | `minimal_output`, `--jq` with the needed fields, a tool in `tools/` |
| Tokens | High `peak` context, many calls per ticket | Fewer tickets per run (a result is read again by each later call), subagents for searches |
| Tokens | Sink `output` large | Shorter reports and PR text, less thinking on routine steps |
| Local | Permission denials in local runs | Add the safe command to `.claude/settings.json` |

## 3. Make the improvement

One change per review, for the largest loss above the threshold. Write down the numbers that the change must make
better ("before" numbers) before you change something.

**Choose the strongest fix** (#1909). A fix has three levels:
1. A rule: text in `CLAUDE.md`, `docs/LEARNINGS.md` or a skill. Each agent must remember it, and each run loads it.
2. A check that fails: a test, a CI step, a lint.
3. A structure that prevents the fault: a data file, a merge driver, a generator.

Use the highest level that is in proportion to the loss. When a loss comes back in the 50 merged PRs after its fix, the
next fix goes one level up. A level-1 rule that stays is debt: make a ticket for its level-2 or level-3 fix.

**Fix all places** (#1909). Before you make the ticket, find all other places with the same pattern (Grep, `ast`,
a lint). Make one epic for all of them (`ticket` skill), with the place of this loss as the first
sub-issue: the pilot. The other sub-issues can wait for the numbers of the pilot ("Start after: N PRs after #M"), but the epic and
its full scope exist at once, so the owner sees the whole plan. #1702 moved one table to a data file and waited
24 hours; the owner then made the epic #1909 for all tables.

**Each bottleneck is a ticket on the board** (owner, 2026-10-27). For the bottleneck of step 2, look for an open
ticket with the title `Process: <bottleneck>` (a data gap: `Process: measure <what>`). None → make one (`ticket`
skill, labels `process`, `tooling`, `P1`): the evidence (the numbers and their period), the before-numbers, the
hypothesis (what causes the loss, or the question that the new data must answer), and one small step. Then do that
step in this review when it is small. Work iteratively: one step per review, measure it in step 0 of the next review
(at least 10 runs), and then close the ticket (the loss is below the threshold, or the data answered the question),
or add the next step to it. A data ticket that names a bottleneck ends with a new ticket for that bottleneck.
First list the open `tooling` and process tickets (`/issues?state=open&labels=tooling`, and titles that start with
"Process:"). When one already names the pattern, do not make a second change: claim that ticket (`tools/claim.py N`)
and do it as this improvement, or, when another run owns it, choose the next pattern. PR #917 of a review and the
ticket #903 made the same change of the autopilot skill at the same time: one PR conflicted and was wasted.

- Small (text in a skill, `CLAUDE.md`, `LEARNINGS.md`, a setting, a workflow step, the setup script): do it now,
  in one PR with the title "Process: <what>" and the label `process`. Verify level 1. Merge it like a ticket.
- Large (a new tool, a test framework change): make a `tooling` ticket with priority `P1`.
- Owner only (environment settings, the scheduled task, GitHub settings): make the change in the repository
  first (for example `scripts/cloud-setup.sh`), then a `needs-human` ticket with numbered steps and the exact
  text to paste. One ticket per change. Look for an open one first.

## 4. Clean up

- `docs/LEARNINGS.md` below 80 lines (only this skill merges and removes lines there; ticket runs only add), `CLAUDE.md` below 150 lines. Remove lines that are no longer true.
- Read the skills for instructions that contradict each other. Correct them.

## 5. Report

Add the change to "Process changes" on the status issue with its before-numbers:
`- <date>: <change> (PR #n) — before: <numbers>` (for example "conflict 12 % of the run minutes, 14 conflicts / 6 h").
Comment 3–5 lines: the result of step 0 and the misses, the numbers of the seven areas, the largest loss, what you changed (or
"no change: largest loss X, below the threshold"), and what you expect. The owner can reject the change in a comment. Then revert it
and add the reason to `docs/LEARNINGS.md`.

Then set the next review: `python3 tools/claim.py 0 --reviewed change` after a change (the next review comes after 200
merged PRs and 4 hours), or `--reviewed none` when no loss was large enough for a change (the gap doubles, at most 800
merged PRs, #898, #1697, #2039, #3465).

## Guardrails

- Never weaken or remove tests, CI checks, lint rules or verify levels to save time.
- Never remove the rule that only the owner (`owner` in `agent.toml`) gives instructions, or the `deny` list in
  `.claude/settings.json`, or the hook `.claude/hooks/guard-main.sh` (it stops the command before it runs; the
  ruleset `Protect main` of the owner only refuses the push). Never allow destructive commands (force-push, delete, `gh api`).
- Never change the priorities that the owner set.
- Explain the reason for each change. If an earlier change did not help (the numbers did not improve),
  revert it.
