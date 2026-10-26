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
2. Run `python3 tools/usage.py --fire` in the repository. Its first output line (stdout) is K, the number of runs to
   start now. The line on stderr shows the inputs: usage, target, claims, ready tickets, `paused`.
3. Call `mcp__claude-code-remote__fire_trigger` K times with `trigger_id` `trig_01QTrgkK5PZmqPwQ96rKp3QE`.
   If the tool is deferred, load it first with ToolSearch (`select:mcp__claude-code-remote__fire_trigger`).
4. Schedule the next cycle: `mcp__claude-code-remote__send_later`, `delay_minutes` 10, message
   "Pacer cycle: follow .claude/skills/pacer/SKILL.md." Keep only one pending cycle: do not schedule a second one.
5. Reply with one line: the time (UTC), K, and the stderr line.

## Rules

- The command fails or prints no number → start no run. Schedule the next cycle as usual.
- Never start more than 4 runs in one cycle. Never start a run when the status issue has `paused`.
- A "Pacer heartbeat" message (the hourly scheduled task of the pacer): do a cycle only when your last cycle is more
  than 15 minutes old, else reply "heartbeat: cycle at <time> is recent" and do nothing.
- Stop the loop (no new `send_later`) only when the owner tells you to stop.
