# Contributing and setup

aoe2mc has one owner (`Larspolo`) and one Claude Max account. Claude Code agents do most of the work without a
person. This file tells you how to set up all parts of that system, from the start: GitHub, the Claude account, the
cloud environment, the scheduled tasks and the pacer. It also tells you which settings to turn off, so that each
run uses as little quota as now.

This file collects the steps. The details are in these documents. When a document and this file are different,
the document is correct:

| Document | Content |
|---|---|
| `docs/SYSTEM.md` | All parts of the agent system, the locks, the pacing, the setup steps of the owner. |
| `docs/OPERATOR.md` | Check, repair, a new project, a move to another Claude account. |
| `docs/STEERING.md` | How the owner steers the agents through GitHub Issues. |
| `docs/ENVIRONMENT.md` | The network hosts and the setup script of the cloud environment. |
| `scripts/allowed-domains.txt` | The allowed domains of the cloud environment: paste the whole file. |
| `CLAUDE.md` | The commands, the code map and the rules of the code. |

## 1. Work on the code by hand

1. Use Python 3.10 or later (CI uses 3.12). Install the packages:

   ```bash
   python3 -m pip install -r requirements-dev.txt
   ```

2. Before each commit, run lint and the fast tests:

   ```bash
   ruff check .
   ```

   ```bash
   python3 -m pytest -n auto
   ```

3. For the server tests (`python3 -m pytest -m mc`) and the in-game screenshots, install Java 25, `xdotool` and
   software Vulkan. `scripts/cloud-setup.sh` shows the packages.
4. Obey the rules of `CLAUDE.md`: one ticket per PR, a failing test first for a bug, new tests in a new file
   `tests/test_<topic>.py`, deterministic output, game data in `.jsonl` files. Write all text in ASD-STE100
   Simplified Technical English.
5. Put scratch output (worlds, scenarios, images) in `out/`. Never commit worlds.
6. To let Automerge merge a PR of your own branch, add the label `automerge` to it.

## 2. GitHub settings

Do these steps one time, in the repository `Larspolo/aoe2mc`:

1. Install the Claude GitHub app on the repository (https://github.com/apps/claude).
2. Keep the repository public. Then GitHub Actions minutes are free (#370).
3. Settings → Rules → Rulesets: add the ruleset `Protect main`. It refuses a force push and a delete of `main`.
4. Settings → Actions → General → Workflow permissions: select "Read and write permissions". Automerge,
   Unconflict, Claims and the Pacer push and merge with `GITHUB_TOKEN`.
5. Settings → Pages → Source: select "GitHub Actions". The workflow `dashboard-site.yml` publishes the owner's
   dashboard there.
6. Settings → Secrets and variables → Actions → Secrets. Add these 7 repository secrets (section 6 tells you where
   to get them):

   | Secret | Value |
   |---|---|
   | `CLAUDE_CODE_OAUTH_TOKEN` | The output of `claude setup-token` on your computer (the quota read of the pacer). |
   | `PACER_URL_MAIN`, `PACER_TOKEN_MAIN` | The fire URL and the token of the API trigger of "aoe2mc autopilot". |
   | `PACER_URL_HAIKU`, `PACER_TOKEN_HAIKU` | The same for "aoe2mc autopilot haiku". |
   | `PACER_URL_DEEP`, `PACER_TOKEN_DEEP` | The same for "aoe2mc autopilot deep". |

7. Actions → Labels → Run workflow. It makes the labels of `.github/labels.txt`.
8. Make sure that issue #1 is open and has the label `agent-status` (the status issue). If it is missing, the
   first run makes it.

## 3. Claude account settings (claude.ai)

These settings are on the account, not in the repository. They make each run use less quota (#3833).

1. Settings → Claude Code → **Classify session states**: turn it **off**. The classification counts towards the
   plan usage, and it ran for each new session, so for each run.
2. Settings → Capabilities → **Connector search**: turn it **off**.
3. **Auto-fix pull requests**: keep it **off**. Automerge and the runs repair the PRs.
4. **Create pull requests automatically**: keep it **off**. Each run makes its own PR
   (`tools/ship_pr.py`).
5. Customize → Connectors: connect only **GitHub**. Do not add other connectors. Each connector adds its tool
   descriptions or its instructions to each call of each run.
6. Customize → Skills and Customize → Plugins: keep them **empty**. All skills of the runs are in
   `.claude/skills/` of the repository.
7. Keep Settings → Capabilities → "Artifacts" and "Run code in the cloud" as you like. A test of 2026-10-29 found
   that they do not change the base of a run (#3833).

You cannot turn off the built-in parts. The built-in skills `anthropic-skills:*` (docs, docx, pdf, pptx, xlsx,
built-in browser, Chrome browser, computer use) and the Claude Docs instructions have no switch. The repository
removes all other unused tools (section 5).

## 4. Cloud environment

Use one cloud environment (now `Default`) for all scheduled tasks. Open it at claude.ai/code: the environment menu in
the session title bar → Edit.

1. **Network access**: keep "Allow package managers" on. In "Allowed domains", delete the old list and paste the
   whole file [`scripts/allowed-domains.txt`](scripts/allowed-domains.txt). It has one host per line.
   When an agent needs a new host, it adds the host to the file in its PR and opens a `needs-human` ticket that asks
   you to paste the file again (`docs/ENVIRONMENT.md`, section "Network").
2. **Setup script**: paste the full content of `scripts/cloud-setup.sh`. Click **Save**. The cloud keeps the result
   as a snapshot for about 7 days.
3. When `SETUP_VERSION` in `scripts/cloud-setup.sh` changes, the SessionStart hook sees it, and a run opens a
   `needs-human` ticket. Then paste the file again.
4. The environment has no list of connectors. Do not add environment variables or network secrets: the runs do
   not need them.

## 5. Settings in the repository (no action)

The repository already holds these settings. Every session reads them from `main`. Do not change them in the
account:

| File | What it does for the quota |
|---|---|
| `.claude/settings.json`, `disableBundledSkills: true` | Removes the bundled Claude Code skills from each session. |
| `.claude/settings.json`, `permissions.deny` | Removes the session tools that no skill uses (`Artifact`, `Workflow`, `Cron*`, the plan, worktree, task-list, notification, `Suggest*` and `Search*` tools, `mcp__Claude_Docs`, `mcp__ccd_session`, `mcp__claude-code-remote` ...). Their descriptions were about 19,000 of the 66,000 base tokens of each call (#3424). Keep the list in the repository: a rule that a hook writes works only from the next session. |
| `.claude/settings.json`, `permissions.allow` | Lets the runs use `python3`, `git`, `gh api` and the GitHub tools with no prompt. |
| `.claude/hooks/` | `session-start.sh` (packages, the `merge=jsonl` driver, `TMPDIR`, the setup version), `guard-main.sh` and `guard-shell.sh` (block a force push and known shell pitfalls). |
| `.claude/skills/scheduled/SKILL.md` | The rules of a scheduled run. So the prompt of each task is only one line, and a PR changes the rules. |
| `agent.toml` | The project values and the pacing (`[pacing]`: `max_runs`, `max_fire`, `week_guard`, `pacer`, `trigger` ...). |

The skills `dashboard-refresh`, `operator` and `pacer` were removed (#3424, #3438, #3427). Do not add them again.

## 6. Scheduled tasks

Make 3 scheduled tasks at claude.ai/code → Scheduled tasks (routines). **None of them has a schedule.** The pacer
starts them through their API triggers (#3193, #3194). A schedule on a task starts runs that the quota target
did not ask for.

| Setting | "aoe2mc autopilot" | "aoe2mc autopilot haiku" | "aoe2mc autopilot deep" |
|---|---|---|---|
| Prompt | `/scheduled max` | `/scheduled max lane haiku` | `/scheduled max lane deep` |
| Model | Opus 5.5 (`claude-opus-5-5`) | Haiku 5.5 (`claude-haiku-5-5`) | Opus 5.5 (`claude-opus-5-5`) |
| Effort | low | (no setting) | high |
| Schedule | none | none | none |
| Trigger | API trigger | API trigger | API trigger |
| On each fire | a new session | a new session | a new session |
| Repository | `Larspolo/aoe2mc` | `Larspolo/aoe2mc` | `Larspolo/aoe2mc` |
| Cloud environment | the environment of section 4 | the same | the same |
| Connectors | none | none | none |
| State | enabled | enabled | enabled |

Do these steps for each task:

1. Open the task → the menu next to its name → **Edit**.
2. Write the prompt of the table. Write only that line: the skill `scheduled` holds the rules.
3. Select the model in the model selector of the prompt box, and set the effort.
4. **Advanced settings** → **General** → **Repository**: `Larspolo/aoe2mc`. Below it, select the cloud environment of
   section 4.
5. Remove each schedule. Add an **API trigger**. Generate a token. Copy the fire URL and the token into the secrets
   `PACER_URL_<TASK>` and `PACER_TOKEN_<TASK>` (section 2, step 6). A new token makes the old one invalid: then change
   the secret too.
6. Click **Save changes**.

After you make "aoe2mc autopilot", write its trigger ID into `trigger` in `[pacing]` of `agent.toml` (a PR).

The lane tasks are optional. Without one, the pacer starts all runs on the main task. To stop a lane, disable its
task.

Delete these old tasks if they exist: "aoe2mc pacer heartbeat" and "aoe2mc dashboard refresh". The workflows
`pacer.yml` and `dashboard-site.yml` do their work now. Do not keep a long-lived pacer session either.

## 7. Start the pacer

1. Make sure that `pacer = "workflow"` is in `[pacing]` of `agent.toml`.
2. GitHub → Actions → **Pacer** → **Run workflow**. One run loops for 5.5 hours and starts the next run itself.
   The cron `*/30` only restarts a loop that stopped.
3. GitHub → Actions → **Dashboard site** → **Run workflow** one time.
4. After 20 minutes, run the check:

   ```bash
   python3 tools/operator_check.py
   ```

   Each line must be `OK`. Also see `docs/OPERATOR.md`, section 1.

## 8. Workflows (no action)

All workflows start by themselves. You can start them by hand with Actions → the workflow → Run workflow.

| Workflow | When it runs |
|---|---|
| `ci.yml` | Each PR (quick checks), each push to `main`, each night at 03:17 (the full suite). |
| `automerge.yml` | After CI, and every 5 minutes. |
| `unconflict.yml` | Every 20 minutes, and after each merge. |
| `pacer.yml` | A loop with a cycle every 10 minutes; the cron `*/30` restarts it. |
| `dashboard.yml` | Each pacer cycle (10 minutes); the cron `*/10` as a fallback. |
| `dashboard-site.yml` | Each pacer cycle; the cron `*/30` as a fallback. |
| `metrics.yml` | The cron `4,19,34,49 * * * *` (a fallback of the pacer). |
| `close.yml` | Each hour, and on the label `close`. |
| `claims.yml` | When a ticket closes, after each merge, and each day at 05:53. |
| `coverage.yml` | Each push to `main`. |
| `labels.yml` | A change of `.github/labels.txt`. |
| `bundles.yml`, `installers.yml`, `worlds.yml` | The app bundles, the installers of a tag `v*` and the example worlds. |

GitHub fires the cron schedules of this repository only a few times per day. So the pacer loop starts the
dashboard, the dashboard site and the metrics in each cycle.

## 9. Your own computer (optional)

Use a local Claude Code session in a clone of the repository for the work that needs a window:

- `/human`: guides you through the tickets that wait for you (label `needs-human`).
- `/demo`: starts a demo game and makes a ticket for each feedback in the Minecraft chat.
- `scripts/autopilot.sh N`: N work cycles on your computer. It needs the Claude Code CLI and `gh auth login`.

## 10. Steer and stop

- Steer through GitHub Issues: `docs/STEERING.md`.
- Stop all runs: add the label `paused` to issue #1. Remove it to continue.
- Stop one PR: add the label `hold` to it.
- Move to another Claude account: `docs/OPERATOR.md`, section 4.
