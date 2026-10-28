# Operator guide: check, repair, set up and move the start of the runs

This guide replaces the skill `operator` (owner, 2026-10-28). Do the steps yourself, or start a session at
claude.ai/code with the repository and write "Follow docs/OPERATOR.md, section N". A run cannot do sections 1b–4:
it has no trigger or session tools (#566). NAME is the name of `repo` in `agent.toml`.

The runs start from these parts (`docs/SYSTEM.md`, "Setup steps of the owner", steps 4–8):

| Part | Expected |
|---|---|
| Scheduled task "NAME autopilot" | No schedule (the pacer starts it), enabled, the repository of `agent.toml`, the prompt of `docs/SYSTEM.md` step 4, Opus 5.5 at effort low, an API trigger. |
| Scheduled task "NAME autopilot <lane>" for each lane of `weights` in `[pacing]` of `agent.toml` | No schedule, a new session on each fire, enabled, the same prompt with "the argument max lane <lane>", an API trigger. haiku: Haiku 5.5. deep: Opus 5.5 at effort high. |
| Workflow `pacer.yml` (`pacer = "workflow"` in `agent.toml`, #3193) | One run `in_progress` (the loop), the last completed runs green, the secrets `CLAUDE_CODE_OAUTH_TOKEN`, `PACER_URL_<TASK>` and `PACER_TOKEN_<TASK>` for `MAIN`, `HAIKU`, `DEEP`. |

## 1. Check

1. Run `python3 tools/operator_check.py` in the repository. It checks the quota and the target, `paused`, the ready
   tickets, CI on main and the night CI, agent PRs open more than 30 minutes, the labels and the owner comments
   without an answer. Each line is `OK` or `PROBLEM`. Exit 1: at least one problem.
2. Scheduled tasks (claude.ai/code → Scheduled tasks, or `list_triggers` and `get_trigger` in a session): each task
   of the table exists, is enabled, has no schedule and has an API trigger. `trigger` in `[pacing]` of `agent.toml`
   is the ID of "NAME autopilot".
3. Pacer: GitHub → Actions → Pacer. One run is `in_progress`. A red run with "failed: <task>: HTTP 401" is a wrong
   or old token of that task.
4. Runs: the scheduled tasks show a start in the last 2 hours. None while `operator_check.py` shows a target above 0
   and ready tickets is a problem of the pacer or of the tasks.

## 2. Repair

| Problem | Repair |
|---|---|
| No `pacer.yml` run `in_progress` | GitHub → Actions → Pacer → Run workflow (or `gh api repos/OWNER/NAME/actions/workflows/pacer.yml/dispatches -X POST -f ref=main`). |
| A red `pacer.yml` run with "HTTP 401" | Make a new API token of that task (the task → edit → API trigger) and change the secret `PACER_TOKEN_<TASK>`. |
| A scheduled task is off | Enable it in the app (or `update_trigger` with `enabled` true). |
| A scheduled task is missing | Make it as section 3, steps 2 and 3. |
| A prompt differs from `docs/SYSTEM.md` step 4 | Edit the task in the app (or `update_trigger` with the text of step 4). |
| `trigger` in `agent.toml` is not the ID of "NAME autopilot" | A PR that changes `trigger` in `[pacing]` (Automerge merges it). |
| A label is missing | Run the Labels workflow, or make the label from `.github/labels.txt`. |
| No run in 2 hours, target above 0 | Start "NAME autopilot" once by hand, then check the pacer (1.3). |
| Red CI on main, old PRs | Nothing: the next run does it (autopilot step 2). |

To stop a lane, disable its task: the pacer then starts all runs on the main task.

## 3. Set up a new project

1. Run `python3 tools/bootstrap.py DIR --repo OWNER/NAME --github` (#906). It writes `agent.toml` and prints the
   GitHub and environment steps. Do them.
2. Make the scheduled task "NAME autopilot": no schedule, the repository and the cloud environment, the prompt of
   `docs/SYSTEM.md` step 4 with the repository name, Opus 5.5 at effort low.
3. Make "NAME autopilot <lane>" for each lane of `weights` in `[pacing]`: no schedule, a new session on each fire, the
   same prompt with "the argument max" changed to "the argument max lane <lane>", the model and the effort of the table.
4. Make an API trigger for each task, and the secrets of `docs/SYSTEM.md` step 5 (`claude setup-token` for
   `CLAUDE_CODE_OAUTH_TOKEN`, the fire URL and the token of each task).
5. A PR with the ID of "NAME autopilot" in `trigger` and `pacer = "workflow"` in `[pacing]` of `agent.toml`.
6. After the merge: GitHub → Actions → Pacer → Run workflow. Then do section 1.

## 4. Move to another Claude account

Do the steps in sequence. The GitHub side (tickets, claims, labels, the status issue) does not change.

1. Add the label `paused` to the status issue. All runs stop at it, so the two accounts never run at the same time.
2. In the OLD account: disable each scheduled task whose name starts with "NAME " (their API tokens stop with them).
3. In the NEW account: connect GitHub. The Claude GitHub app stays on the repository.
4. In the NEW account: make the cloud environment of `docs/SYSTEM.md` step 2 ("Allow package managers" on, the hosts
   of `docs/ENVIRONMENT.md`, "Network", and the whole file `scripts/cloud-setup.sh` as the setup script).
5. Make the scheduled tasks and the API triggers in the new account: section 3, steps 2–4.
6. A PR with the new ID of "NAME autopilot" in `trigger` of `[pacing]` in `agent.toml`.
7. After the merge: start the workflows "Pacer" and "Dashboard site" once.
8. Remove the label `paused`. Then do section 1.
