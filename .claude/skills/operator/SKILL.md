---
name: operator
description: Check and repair the parts that start the runs of aoe2mc (the scheduled tasks and the pacer session), set them up for a new project, and move them to another Claude account ("/operator move"). Only for a session that the owner starts and types "/operator" in. Runs cannot use it - they have no trigger or session tools (#566).
---

# Operator: check and repair the start of the runs

The runs start from these parts (`docs/SYSTEM.md`, "Setup steps of the owner", steps 4–8):

| Part | Expected |
|---|---|
| Scheduled task "aoe2mc autopilot" | No schedule (the pacer starts it), enabled, repository `repo` of `agent.toml`, the prompt of `docs/SYSTEM.md` step 4. |
| Workflow `pacer.yml` (`pacer = "workflow"` in `agent.toml`, #3193) | One run `in_progress` (the loop), the last completed runs green; each autopilot task has an API trigger (`api_token_hint` in `get_trigger`) and the secrets `PACER_URL_<TASK>`, `PACER_TOKEN_<TASK>`. |
| Fallback, only with `pacer = "session"`: pacer session "aoe2mc pacer" and the task "aoe2mc pacer heartbeat" | The session alive, its last cycle less than 15 minutes old, model Haiku, skill `pacer`; the heartbeat hourly at :36, bound to the session. |
| Scheduled task "aoe2mc autopilot <lane>" for each lane of `weights` in `[pacing]` of `agent.toml` (haiku #1715, deep 2026-10-28) | No schedule (the pacer fires it), a new session on each fire (not bound to a session), enabled, the prompt of the autopilot task with the argument `max lane <lane>`; haiku: model `claude-haiku-5-5`; deep: model `claude-opus-5-5` at effort high. The main task runs at effort low. |

A run of the autopilot task cannot check or repair them: it has no trigger or session tools (#566). A session that
the owner starts has them. So the owner starts a session and types `/operator`; no long-lived owner session is
necessary. Write in ASD-STE100 (CLAUDE.md, "Language").

## Tools

The session tools are in the MCP server `claude-code-remote`. They are deferred: load them first with ToolSearch
(`+claude-code-remote`). This skill uses `list_triggers`, `get_trigger`, `update_trigger`, `create_trigger`,
`fire_trigger`, `list_sessions`, `get_session`, `list_events`, `create_session`, `send_later` and the archive tool of
the sessions (`archive_session`). When a name differs, use the tool of the same function and fix the name here.
Do not write a trigger ID or a session ID into git, except the ID of the autopilot task in `trigger` of `[pacing]` in
`agent.toml` (the pacer reads it, #1898): read the IDs with `list_triggers` and `list_sessions` (tag or title `pacer`).
Without `claude-code-remote` tools (a run, a local CLI): do only part 1a and say that the rest needs an owner session.

## 1. Check

a. Run `python3 tools/operator_check.py` in the repository. It checks what needs no session tools: the quota and the
   target (`tools/usage.py`), `paused`, the ready tickets (`tools/dashboard.py --next`), CI on main and the night CI,
   agent PRs open more than 30 minutes, the labels of `.github/labels.txt` on GitHub, the owner comments without an
   answer (`tools/feedback.py`, #971). Each line is `OK` or `PROBLEM`. Exit 1: at least one problem.
b. **Scheduled tasks** (`list_triggers`, then `get_trigger` for each one): the autopilot tasks exist, are enabled and
   have no cron; each has an API trigger (`api_token_hint`); the autopilot prompt has each point of
   `docs/SYSTEM.md` step 4; `trigger` in `[pacing]` of `agent.toml` is the ID of the autopilot task; each lane of
   `weights` has its task (the table above). Only with `pacer = "session"`: the heartbeat (`36 * * * *`, prompt
   "Pacer heartbeat: follow .claude/skills/pacer/SKILL.md.", `persistent_session_id` the pacer session of 1c). `get_trigger` does not show the effort: ask
   the owner once when a task is new.
c. **Pacer.** With `pacer = "workflow"`: `gh api repos/OWNER/NAME/actions/workflows/pacer.yml/runs?per_page=5`. No run
   `in_progress` is a problem (repair: start the workflow, `/actions/workflows/pacer.yml/dispatches -f ref=main`).
   A red run: read its log (`mcp__github__get_job_logs`): "failed: <task>: HTTP 401" is a wrong or old token (the
   owner makes a new API token and changes the secret). The `last_run.fired_at` of the tasks (`get_trigger`) shows
   the starts. With `pacer = "session"`, the **pacer session** (`list_sessions`, `get_session`, `list_events`): it exists and is not archived; its last
   event is a "Pacer cycle" reply less than 15 minutes old; it has one pending `send_later`; its context use. A
   context above 600,000 tokens, or a last cycle older than 75 minutes (the heartbeat did not wake it), is a problem.
d. **Runs**: the sessions of the autopilot task in the last 2 hours (`list_sessions`). None while
   `operator_check.py` shows a target above 0 and ready tickets is a problem of the pacer or the autopilot task.

## 2. Repair

Ask the owner before each repair, with one line: what is wrong and what the repair does. Do it only after a yes.

| Problem | Repair |
|---|---|
| `pacer = "workflow"`: no `pacer.yml` run `in_progress` | Start it: `gh api repos/OWNER/NAME/actions/workflows/pacer.yml/dispatches -X POST -f ref=main`. |
| `pacer = "workflow"`: a red `pacer.yml` run with "failed: <task>: HTTP 401" | Ask the owner (on the issue, `owner.md`) to make a new API token of that task and change the secret `PACER_TOKEN_<TASK>`. |
| Only with `pacer = "session"`: pacer session dead, archived, stalled, or its context above 600,000 tokens | `create_session` (repository and environment of the autopilot task, model Haiku, title "aoe2mc pacer", message "Pacer cycle: follow .claude/skills/pacer/SKILL.md."), then delete the pending "Pacer cycle" `send_later` of the old session (else two pacers run), then `create_trigger` "aoe2mc pacer heartbeat" again (cron `36 * * * *`, the same prompt, `persistent_session_id` the new session, `initiation` human_request) and delete the old heartbeat: `update_trigger` cannot change `persistent_session_id`. Then archive the old session. If the auto mode denies a delete, set that task to `enabled` false and ask the owner to delete it in the app. |
| A scheduled task is off | `update_trigger` with `enabled` true. |
| The owner asks for the workflow pacer (#3193) | The owner makes the secrets and API triggers of `pacer.yml` (`docs/SYSTEM.md`, step 5). Then a PR with `pacer = "workflow"` in `[pacing]` of `agent.toml`. After its merge: run the workflow "Pacer" by hand and read its log, then delete the pending "Pacer cycle" `send_later` of the pacer session, set "aoe2mc pacer heartbeat" to `enabled` false, and archive the pacer session. With the workflow pacer, check its last runs (green, "Started") in place of the pacer session (1c). |
| A lane task is missing, or the owner asks for a lane | As section 5, steps 5 and 6, for that lane. For the Haiku lane in detail: `get_trigger` of the autopilot task, then `create_trigger` "aoe2mc autopilot haiku" with `create_new_session_on_fire` true (else it fires into this session, #1718), no cron and no `run_once_at`, the same repository and environment, `initiation` human_request, and its prompt with "the argument max" replaced by "the argument max lane haiku". Then `update_trigger` with `model` `claude-haiku-5-5` (the owner asked for it). To stop the lane: `update_trigger` with `enabled` false; the pacer then starts all runs on Opus. A Haiku task bound to a session (`persistent_session_id`): `update_trigger` with `enabled` false and the name "aoe2mc autopilot haiku (wrong, delete)", make the task again, and ask the owner to delete the wrong one in the app (the auto mode can deny a delete). |
| A scheduled task is missing | `create_trigger` with the values of section 3. |
| A prompt or a cron differs from `docs/SYSTEM.md` | `update_trigger` with the text of `docs/SYSTEM.md`. |
| `trigger` in `agent.toml` is not the autopilot task | A PR that changes `trigger` in `[pacing]` of `agent.toml` (Automerge merges it). |
| A label is missing | Run the Labels workflow (`/actions/workflows/labels.yml/dispatches -f ref=main`), or make the label with `gh api repos/OWNER/NAME/labels -f name=... -f color=... -f description=...` from `.github/labels.txt` (#980). |
| No run in 2 hours, target above 0 | `fire_trigger` of the autopilot task once, then check the pacer (1c). |
| Owner comments without an answer | `fire_trigger` of the autopilot task once: its step 3 answers them. |
| Red CI on main, old PRs | Nothing here: the next run does it (autopilot step 2). Name them in the report. |

## 3. Setup for a new project

For a new repository, first run `python3 tools/bootstrap.py DIR --repo OWNER/NAME --github` (#906): it writes
`agent.toml` and prints the GitHub and environment steps. Then, with the values of `agent.toml`:
1. `create_trigger` "NAME autopilot": no cron (the pacer starts it), the repository and the environment, the prompt of
   `docs/SYSTEM.md` step 4 with the repository name.
2. `create_session` "NAME pacer" (model Haiku), message "Pacer cycle: follow .claude/skills/pacer/SKILL.md.". Write the
   trigger ID of step 1 into `trigger` of `[pacing]` in `agent.toml` and push it (a PR).
3. `create_trigger` "NAME pacer heartbeat": cron `36 * * * *`, prompt "Pacer heartbeat: follow
   .claude/skills/pacer/SKILL.md.", `persistent_session_id` the session of step 2.
4. The lane tasks and their owner settings: section 5, steps 5 and 6.
   Steps 2 and 3 start the session pacer (a new `agent.toml` has no `pacer` key: "session"). For the workflow pacer
   (#3193) the owner does `docs/SYSTEM.md` step 5 (the secrets and API triggers); then a PR with `pacer = "workflow"`,
   and the repair row "The owner asks for the workflow pacer" of section 2.
5. Do the checks of section 1.

## 4. Report

Reply in a few lines: what is OK, what you repaired (with the new session or trigger names), and what only the owner
can do, with exact steps (for example a GitHub setting or the environment of `docs/SYSTEM.md` steps 1 and 2). Do not
comment on GitHub and do not use PushNotification: the owner reads the session.

## 5. Move to another account (`/operator move`)

The owner starts this session in the NEW Claude account, with the repository, and types `/operator move`. The session
tools see only the parts of this account: the old tasks and the old pacer stay in the old account until the owner
stops them. Do the steps in sequence. A step "Owner:" is for the owner: give the exact values below (and the result
of `read_documentation` for its topic, when the session has that tool: it shows the owner the place in the app),
then wait for "done" and check the result. When the auto mode denies a call, give the owner the same change as an
owner step. NAME is the name of `repo` in `agent.toml`.

1. Pause: add the label `paused` to the status issue. The runs and the pacers of both accounts stop at it (autopilot
   step 1, pacer rules), so the two accounts never run at the same time.
2. Owner, in the OLD account: claude.ai/code → Scheduled tasks: disable each task whose name starts with "NAME "
   (autopilot, the lane tasks, pacer heartbeat, a dashboard refresh); Sessions: archive "NAME pacer" (if one runs).
   Else the old pacer starts runs again after step 9. The workflow pacer then gets HTTP 400 from the old tasks
   until step 7 puts the secrets of the new tasks.
3. Owner, in the NEW account: connect GitHub (topic `github.access`). The Claude GitHub app stays on the repository.
   Check: `gh api repos/OWNER/NAME --jq .permissions.push` prints `true` in this session.
4. Owner: make the cloud environment (`docs/SYSTEM.md`, "Setup steps of the owner", step 2): "Allow package
   managers" on, the hosts of `docs/ENVIRONMENT.md` ("Network"), the setup script `scripts/cloud-setup.sh` (paste the
   whole file; topics `environment.network` and `environment.setup_script`). Check: `list_environments` shows it;
   keep its `environment_id`.
5. `create_trigger` for each task, with the environment of step 4 and `initiation` human_request: "NAME autopilot"
   (cron `6 * * * *`, the text `PROMPT` of `tools/bootstrap.py` with the values of `agent.toml`), and "NAME autopilot
   <lane>" for each lane of `weights` in `[pacing]` (no cron, `create_new_session_on_fire` true, the same prompt with
   "the argument max" changed to "the argument max lane <lane>").
6. Owner: the tool cannot set the repository, the model or the effort. In the app (Scheduled tasks → the task →
   edit), for each task of step 5: the repository OWNER/NAME; "NAME autopilot": Opus 5.5, effort low; "NAME autopilot
   haiku": Haiku 5.5; "NAME autopilot deep": Opus 5.5, effort high. Check: `get_trigger` shows the model and the
   repository of each.
7. Start the pacer. With `pacer = "workflow"`: the owner makes the secrets of `docs/SYSTEM.md` step 5 again for the
   new account (a new `claude setup-token` and the API triggers of the new tasks); then start the workflow "Pacer"
   once. With `pacer = "session"`: `create_session` (the environment of step 4, `source_url` of the repository, model
   `claude-haiku-5-5`, title "NAME pacer", prompt "Pacer cycle: follow .claude/skills/pacer/SKILL.md."), then
   `create_trigger` "NAME pacer heartbeat" (cron `36 * * * *`, `persistent_session_id` the new session, prompt
   "Pacer heartbeat: follow .claude/skills/pacer/SKILL.md.").
8. The new values in git, one PR (Automerge merges it): `trigger` in `[pacing]` of `agent.toml` is the ID of "NAME
   autopilot" (the pacer reads it, #1898). The dashboard page belongs to the old account: publish
   `tools/dashboard_artifact/index.html` as a new artifact (load the artifact skills first; read the old page with
   the Artifact tool for its capabilities while the owner can still open it), put its URL into `artifact` of
   `[dashboard]`, and run the `dashboard-refresh` skill once.
9. Remove the label `paused`. Do the checks of section 1, then report as in section 4: what is ready, and each owner
   step that is still open.
