---
name: improve
description: Review how efficiently the agent works on aoe2mc and make one concrete improvement to its own process (CLAUDE.md, skills, tools, tests, settings). Use every 5th autopilot run, after a run that failed or took more than 90 minutes, or when the owner asks for a process review.
---

# Improve the process

The aim: more closed tickets for the same usage, with the same quality. Make one good improvement per
review. Do not make many small changes.

## 1. Collect the data

- The last 20 run comments by the agent on the status issue (label `agent-status`). Each has a line
  `Metrics: ticket #n · size · result · minutes · CI runs · time sinks: ...`.
- The tickets and PRs closed in that period, failed CI runs (`actions_list`), and tickets that the owner
  reopened or that came from owner feedback on merged work (rework).
- `docs/LEARNINGS.md` and the "Process changes" list on the status issue (what was tried before).

## 2. Find the largest loss

Compute: tickets per run, median minutes for `size:S` and `size:M` tickets (last 5 runs against the 5 runs
before), CI runs per PR, blocked and rework counts. Then find the one pattern that costs the most.
Typical patterns and their fixes:

| Pattern | Fix |
|---|---|
| Much reading to find code | Better code map in `CLAUDE.md`, or a short `docs/architecture.md` |
| The same manual check again and again | A tool in `tools/` or a test fixture |
| The same kind of ticket again (for example a new building design) | A dedicated skill in `.claude/skills/` |
| CI red after the push | Add the failing check to the local verify level, or fix the flaky test |
| Permission denials in local runs | Add the safe command to `.claude/settings.json` |
| Unclear tickets, many questions | A better form in the `ticket` skill, ask earlier |
| Rework after owner feedback | A rule from the feedback in `CLAUDE.md` |
| Runs longer than 90 minutes | Stricter size rules, split earlier |
| Slow tests | Faster fixtures, or move a test to the slow suite |

## 3. Make the improvement

- Small (text in a skill, `CLAUDE.md`, `LEARNINGS.md`, a setting): do it now, in one PR with the title
  "Process: <what>". Verify level 1. Merge it like a ticket.
- Large (a new tool, a test framework change): make a `tooling` ticket with priority `P1`.

## 4. Clean up

- `docs/LEARNINGS.md` below 80 lines, `CLAUDE.md` below 150 lines. Remove lines that are no longer true.
- Read the skills for instructions that contradict each other. Correct them.

## 5. Report

Add the change to "Process changes" on the status issue. Comment 3–5 lines: the numbers, the pattern you
found, what you changed, and what you expect. The owner can reject the change in a comment. Then revert it
and add the reason to `docs/LEARNINGS.md`.

## Guardrails

- Never weaken or remove tests, CI checks, lint rules or verify levels to save time.
- Never remove the rule that only the owner (`Larspolo`) gives instructions, or the `deny` list in
  `.claude/settings.json`. Never allow destructive commands (force-push, delete, `gh api`).
- Never change the priorities that the owner set.
- Explain the reason for each change. If an earlier change did not help (the numbers did not improve),
  revert it.
