---
name: improve
description: Review how efficiently the agent works on aoe2mc and make one concrete improvement to the whole system (CLAUDE.md, skills, tools, tests, CI workflows, the cloud setup script, settings). Use every 5th autopilot run, after a run that failed or took more than 90 minutes, or when the owner asks for a process review.
---

# Improve the process

The aim: more closed tickets for the same usage, with the same quality. Look at the whole system, not only
the skills: the agent process, CI, the cloud environment, the repository and the scheduling of the runs.
Make one good improvement per review. Do not make many small changes.

## 1. Collect the data

Run `python3 tools/health.py` first (`--hours N`, default 24, about 25 s). It prints the CI runs per workflow,
the slowest CI steps, the setup minutes, takeovers, releases, merge conflicts, claim-to-merge minutes and files
that do not belong in git. Collect by hand only what it does not print.

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

## 2. Find the largest loss

Compute the numbers of all five areas: tickets per run, median minutes for `size:S` and `size:M` tickets
(last 5 runs against the 5 runs before), setup minutes, local check rounds per PR, GitHub Actions minutes per day (the account has 2,000 per month: keep
the use below about 50 per day), nightly CI failures that are
not in the code, rework, takeovers and conflicts. Then find the one pattern that costs the most. Typical
patterns and their fixes:

| Area | Pattern | Fix |
|---|---|---|
| Agent | Much reading to find code | Better code map in `CLAUDE.md`, or a short `docs/architecture.md` |
| Agent | The same manual check again and again | A tool in `tools/` or a test fixture |
| Agent | The same kind of ticket again (for example a new building design) | A dedicated skill in `.claude/skills/` |
| Agent | Unclear tickets, many questions | A better form in the `ticket` skill, ask earlier |
| Agent | Rework after owner feedback | A rule from the feedback in `CLAUDE.md` |
| Agent | Runs longer than 90 minutes | Stricter size rules, split earlier |
| CI | Nightly CI red, or main red at the start of a run | Add the failing check to the local checks (autopilot 6.8), or fix the flaky test |
| CI | More than about 50 Actions minutes per day | Fewer scheduled workflow runs, or move the job into the local checks |
| CI | A slow step (install, download) | `actions/cache` with the correct path and key, or a smaller install |
| CI | A cache that is never restored ("Cache not found") | Correct the cache path or key |
| CI | Slow tests | Faster fixtures, or move a test to the slow suite |
| Environment | Runs install or download the same thing | Add it to `scripts/cloud-setup.sh` |
| Environment | `setup` more than 3 minutes | Move work from the SessionStart hook to the setup script |
| Environment | A blocked host, a missing variable | `needs-human` ticket with the exact host or name |
| Repository | Files in git that do not belong there | `.gitignore`, and a test that fails on such files |
| Scheduling | Dead claims, stalled PRs | Better claim or takeover rules (`tools/claim.py`, autopilot) |
| Scheduling | Merge conflicts in generated files | A merge driver in `.gitattributes`, or generate the file in CI |
| Scheduling | Runs stop because no ticket is ready | Split epics earlier |
| Local | Permission denials in local runs | Add the safe command to `.claude/settings.json` |

## 3. Make the improvement

- Small (text in a skill, `CLAUDE.md`, `LEARNINGS.md`, a setting, a workflow step, the setup script): do it now,
  in one PR with the title "Process: <what>". Verify level 1. Merge it like a ticket.
- Large (a new tool, a test framework change): make a `tooling` ticket with priority `P1`.
- Owner only (environment settings, the scheduled task, GitHub settings): make the change in the repository
  first (for example `scripts/cloud-setup.sh`), then a `needs-human` ticket with numbered steps and the exact
  text to paste. One ticket per change. Look for an open one first.

## 4. Clean up

- `docs/LEARNINGS.md` below 80 lines (only this skill merges and removes lines there; ticket runs only add), `CLAUDE.md` below 150 lines. Remove lines that are no longer true.
- Read the skills for instructions that contradict each other. Correct them.

## 5. Report

Add the change to "Process changes" on the status issue. Comment 3–5 lines: the numbers, the pattern you
found, what you changed, and what you expect. The owner can reject the change in a comment. Then revert it
and add the reason to `docs/LEARNINGS.md`.

## Guardrails

- Never weaken or remove tests, CI checks, lint rules or verify levels to save time.
- Never remove the rule that only the owner (`Larspolo`) gives instructions, or the `deny` list in
  `.claude/settings.json`, or the hook `.claude/hooks/guard-main.sh` (`main` has no branch protection: the
  repository is private on a free account). Never allow destructive commands (force-push, delete, `gh api`).
- Never change the priorities that the owner set.
- Explain the reason for each change. If an earlier change did not help (the numbers did not improve),
  revert it.
