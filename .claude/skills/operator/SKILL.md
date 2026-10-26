---
name: operator
description: Check and repair the parts that start the runs of aoe2mc (the two scheduled tasks and the pacer session), and set them up for a new project. Only for a session that the owner starts and types "/operator" in. Runs cannot use it - they have no trigger or session tools (#566).
---

# Operator: check and repair the start of the runs

The runs start from three parts (`docs/SYSTEM.md`, "Setup steps of the owner", steps 4–6):

| Part | Expected |
|---|---|
| Scheduled task "aoe2mc autopilot" | Hourly at :06, enabled, repository `repo` of `agent.toml`, the prompt of `docs/SYSTEM.md` step 4. |
| Pacer session "aoe2mc pacer" | Alive, the last cycle less than 15 minutes old, model Haiku, skill `pacer`. |
| Scheduled task "aoe2mc pacer heartbeat" | Hourly at :36, enabled, fires into the pacer session (`persistent_session_id`). |

A run of the autopilot task cannot check or repair them: it has no trigger or session tools (#566). A session that
the owner starts has them. So the owner starts a session and types `/operator`; no long-lived owner session is
necessary. Write in ASD-STE100 (CLAUDE.md, "Language").

## Tools

The session tools are in the MCP server `claude-code-remote`. They are deferred: load them first with ToolSearch
(`+claude-code-remote`). This skill uses `list_triggers`, `get_trigger`, `update_trigger`, `create_trigger`,
`fire_trigger`, `list_sessions`, `get_session`, `list_events`, `create_session`, `send_later` and the archive tool of
the sessions (`archive_session`). When a name differs, use the tool of the same function and fix the name here.
Do not write a trigger ID or a session ID into git, except the trigger ID that `pacer` already names (the pacer needs
it before the clone): read the IDs with `list_triggers` and `list_sessions` (tag or title `pacer`).
Without `claude-code-remote` tools (a run, a local CLI): do only part 1a and say that the rest needs an owner session.

## 1. Check

a. Run `python3 tools/operator_check.py` in the repository. It checks what needs no session tools: the quota and the
   target (`tools/usage.py`), `paused`, the ready tickets (`tools/dashboard.py --next`), CI on main and the night CI,
   agent PRs open more than 30 minutes, the labels of `.github/labels.txt` on GitHub, the owner comments without an
   answer (`tools/feedback.py`, #971). Each line is `OK` or `PROBLEM`. Exit 1: at least one problem.
b. **Scheduled tasks** (`list_triggers`, then `get_trigger` for each one): both tasks exist and are enabled; the cron
   is `6 * * * *` (autopilot) and `36 * * * *` (heartbeat), in UTC; the autopilot prompt has each point of
   `docs/SYSTEM.md` step 4; the heartbeat prompt is "Pacer heartbeat: follow .claude/skills/pacer/SKILL.md." and its
   `persistent_session_id` is the pacer session of 1c; the trigger ID in `.claude/skills/pacer/SKILL.md` is the ID
   of the autopilot task.
c. **Pacer session** (`list_sessions`, `get_session`, `list_events`): it exists and is not archived; its last
   event is a "Pacer cycle" reply less than 15 minutes old; it has one pending `send_later`; its context use. A
   context above 600,000 tokens, or a last cycle older than 75 minutes (the heartbeat did not wake it), is a problem.
d. **Runs**: the sessions of the autopilot task in the last 2 hours (`list_sessions`). None while
   `operator_check.py` shows a target above 0 and ready tickets is a problem of the pacer or the autopilot task.

## 2. Repair

Ask the owner before each repair, with one line: what is wrong and what the repair does. Do it only after a yes.

| Problem | Repair |
|---|---|
| Pacer session dead, archived, stalled, or its context above 600,000 tokens | `create_session` (repository and environment of the autopilot task, model Haiku, title "aoe2mc pacer", message "Pacer cycle: follow .claude/skills/pacer/SKILL.md."), then `update_trigger` of the heartbeat with the new `persistent_session_id`, then archive the old session. |
| A scheduled task is off | `update_trigger` with `enabled` true. |
| A scheduled task is missing | `create_trigger` with the values of section 3. |
| A prompt or a cron differs from `docs/SYSTEM.md` | `update_trigger` with the text of `docs/SYSTEM.md`. |
| The trigger ID in `pacer` is not the autopilot task | A PR that changes the ID in `.claude/skills/pacer/SKILL.md` (Automerge merges it). |
| A label is missing | Run the Labels workflow (`/actions/workflows/labels.yml/dispatches -f ref=main`), or make the label with `gh api repos/OWNER/NAME/labels -f name=... -f color=... -f description=...` from `.github/labels.txt` (#980). |
| No run in 2 hours, target above 0 | `fire_trigger` of the autopilot task once, then check the pacer (1c). |
| Owner comments without an answer | `fire_trigger` of the autopilot task once: its step 3 answers them. |
| Red CI on main, old PRs | Nothing here: the next run does it (autopilot step 2). Name them in the report. |

## 3. Setup for a new project

For a new repository, first run `python3 tools/bootstrap.py DIR --repo OWNER/NAME --github` (#906): it writes
`agent.toml` and prints the GitHub and environment steps. Then, with the values of `agent.toml`:
1. `create_trigger` "NAME autopilot": cron `6 * * * *`, the repository and the environment, the prompt of
   `docs/SYSTEM.md` step 4 with the repository name.
2. `create_session` "NAME pacer" (model Haiku), message "Pacer cycle: follow .claude/skills/pacer/SKILL.md.". Write the
   trigger ID of step 1 into `.claude/skills/pacer/SKILL.md` and push it (a PR).
3. `create_trigger` "NAME pacer heartbeat": cron `36 * * * *`, prompt "Pacer heartbeat: follow
   .claude/skills/pacer/SKILL.md.", `persistent_session_id` the session of step 2.
4. Do the checks of section 1.

## 4. Report

Reply in a few lines: what is OK, what you repaired (with the new session or trigger names), and what only the owner
can do, with exact steps (for example a GitHub setting or the environment of `docs/SYSTEM.md` steps 1 and 2). Do not
comment on GitHub and do not use PushNotification: the owner reads the session.
