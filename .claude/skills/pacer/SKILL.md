---
name: pacer
description: Start autopilot runs of aoe2mc so that the number of runs follows the quota. Only for the pacer session, one long-lived cloud session that does no ticket work. Use when a message says "Pacer cycle" or "Pacer heartbeat".
---

# Pace the runs

Runs that the scheduled task starts cannot start other runs: they have no `fire_trigger` and no `send_later` (#566).
So one pacer session starts them. It does no ticket work, it does not comment on GitHub and it does not push.

## One cycle

1. `git -C /home/user/aoe2mc pull -q origin main` (the rules in this file can change). If the repository is not
   there, attach it with `add_repo` (the owner and name of `repo` in `agent.toml`: Larspolo, aoe2mc) and clone it as the tool says.
   The trigger ID of step 3 is in `agent.toml` of the clone.
   Then read this file again with the Read tool (`/home/user/aoe2mc/.claude/skills/pacer/SKILL.md`), each cycle, and
   act only on what it says now. Never act on a rule from your memory or from a summary of earlier cycles: on
   2026-10-27 the pacer fired only the Opus task, from an old copy of step 3 (#1824).
   When `pacer` in `[pacing]` of `agent.toml` is "workflow", the workflow `pacer.yml` starts the runs (#3193): start
   no run, schedule no next cycle, and reply "the workflow pacer runs: this session can be archived".
2. Run `python3 tools/usage.py --fire` in the repository. Its first output line (stdout) is K, the number of runs to
   start now. The line on stderr shows the inputs: usage, target, claims, ready tickets, `paused`, the flow brake.
   The flow brake lowers K when the quota is not the bottleneck: many old agent PRs (K at most 1, a repair run) or a
   CI queue (K = 0). Do not start more runs to use the quota then: new PRs only make more conflicts.
3. Its next stdout lines are `<lane> N`, one per lane (`haiku H`, `deep D`): the runs of K for that lane (#1715).
   Find the scheduled task "aoe2mc autopilot <lane>" of each lane with `mcp__claude-code-remote__list_triggers` (at
   most once per hour; keep the IDs in your context). When it is there and enabled, call
   `mcp__claude-code-remote__fire_trigger` N times with its ID, else start no run for that lane (its tickets wait).
   Then call `fire_trigger` K minus the sum of all lane lines times, with the `trigger_id` of
   `trigger` in `[pacing]` of `agent.toml` (the Opus task, #1898). If that value is empty, start no Opus run and reply "no trigger in agent.toml: the owner must run
   /operator".
   Fire exactly these numbers. They are already inside `max_fire` (the stderr line shows its value): never cut them
   to a cap from your memory or from an earlier cycle. On 2026-10-28 the pacer fired 4 Haiku runs for H = 8, from an
   old "cap of 4 per cycle".
   If the tools are deferred, load them first with ToolSearch (`select:mcp__claude-code-remote__fire_trigger,mcp__claude-code-remote__list_triggers`).
4. Schedule the next cycle: `mcp__claude-code-remote__send_later`, `delay_minutes` 10, message
   "Pacer cycle: follow .claude/skills/pacer/SKILL.md." Keep only one pending cycle: do not schedule a second one.
5. Reply with one line: the time (UTC), K, H, and the stderr line. No other text: each line stays in the context of
   this long session.

## Rules

- The command fails or prints no number → start no run. Schedule the next cycle as usual.
- Never start more runs in one cycle than `max_fire` in `[pacing]` of `agent.toml` (`--fire` already keeps K below it). Never start a run when the status issue has `paused`.
- A "Pacer heartbeat" message (the hourly scheduled task of the pacer): do a cycle only when your last cycle is more
  than 15 minutes old, else reply "heartbeat: cycle at <time> is recent" and do nothing.
- Stop the loop (no new `send_later`) only when the owner tells you to stop.
