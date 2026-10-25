# Steering the agent

The agent (Claude Code) works on this project automatically. You steer it asynchronously through GitHub
Issues. You can do all of this in the GitHub app on your phone.

## How the agent works

Each run does one work cycle (the `autopilot` skill):

1. It reads your new comments on issues and PRs, and does what they ask.
2. It sorts new issues: priority, kind and size labels. It splits large tickets.
3. It does the top ticket: code, tests, a PR. It merges the PR when CI passes.
4. It reports on the **Agent status** issue (label `agent-status`) with a short comment. GitHub sends you a
   notification. The dashboard in the issue body is generated from GitHub (`tools/dashboard.py`, workflow
   `Dashboard`): waiting for you, working on, next up, recently done. It updates on each label change and every
   15 minutes. Runs only add the process changes.
5. It improves its own process: it writes learnings, corrects its instructions and makes tooling tickets.
   Every 5th run, the `improve` skill measures the runs (minutes, local checks, time sinks) and makes one larger
   improvement. The status issue lists each process change.

The agent takes instructions only from comments and issues by `Larspolo`.

## What you can do

| You want to | Do this |
|---|---|
| Add a ticket | New issue → **Ticket** form. One or two sentences are enough. |
| Do a ticket next | Give it label `P0`, or comment "do this next". |
| Change a priority | Change the label (`P0` do next, `P1` high, `P2` normal, `P3` later). |
| Give feedback | Comment on the ticket, on the PR, or on the status issue. |
| Reject merged work | Comment on the merged PR. The agent makes a follow-up ticket. |
| Answer a question | Answer in the `needs-human` ticket. The agent removes the label. |
| Stop the agent | Add label `paused` to the status issue. Remove it to continue. |
| Cancel a ticket | Close it as "not planned". |
| Reject a process change | Comment on the status issue. The agent reverts it and notes why. |
| Ask for a process review | Comment "process review" on the status issue. |

Order of work: `P0` → `P1` → `P2` → `P3`. With the same priority, the lowest issue number goes first.
Tickets with `needs-human`, `blocked` or `epic` wait.

## Labels

- Priority: `P0`, `P1`, `P2`, `P3`
- Size: `size:S`, `size:M`, `size:L` (L tickets are split before work starts)
- Kind: `bug`, `feature`, `tooling`, `design`, `docs`, `cleanup`
- Flow: `needs-human`, `blocked`, `in-progress`, `epic`, `agent-status`, `paused`

The file `.github/labels.txt` defines the labels. The Labels workflow creates them on `main`.

## Where the agent runs

- **Scheduled cloud runs** (recommended): a scheduled task in Claude Code on the web starts a new session on
  a timer. Each run uses your Max quota. Change or stop the schedule at claude.ai/code (scheduled tasks).
  The scheduled task must have the repository `Larspolo/aoe2mc`. Without it, the runs cannot clone the code.
  To set it: open claude.ai/code/routines → the task → menu next to its name → **Edit** → **Advanced
  settings** → **General** → **Repository** → `Larspolo/aoe2mc`. Below it, select the **Cloud environment**
  that allows the Mojang hosts. Select the model in the model selector of the prompt box. **Save changes**.
  More runs can work at the same time (start them with **Run now**). They claim tickets with a comment, so two
  runs do not do the same ticket. With the argument `max`, a run continues until no ticket is ready, and it
  starts a fresh run when its context is half full. To stop all runs: add `paused` to the status issue.
- **On your computer**: `scripts/autopilot.sh 3` runs 3 cycles, one ticket each.
  It needs the Claude Code CLI and the GitHub CLI (`gh auth login`).
- **By hand**: open a Claude Code session in this repository and type `/autopilot`.

## Network for Minecraft tests

The agent starts a headless Minecraft server for tests. For this, the environment allows these hosts
(done in #12; cloud environment menu in the session title bar → Edit → Network access → Allowed domains):

    piston-meta.mojang.com
    piston-data.mojang.com
    libraries.minecraft.net

Keep "Allow package managers" on. Steps: https://code.claude.com/docs/en/cloud-environments#network-access

## Setup script (faster start)

Use one cloud environment for all runs. All tickets use the same tools.
`scripts/cloud-setup.sh` installs Java 25, the Python packages and the Minecraft server jars.
The cloud keeps the result as a snapshot for about 7 days, or until you change the script or the network
settings. Then the script runs again one time. To use it: cloud environment menu in the session title bar → Edit →
**Setup script** → paste the content of `scripts/cloud-setup.sh` → **Save**. When the file changes, the agent
sees it at the start of a session (the SessionStart hook compares `SETUP_VERSION`) and opens a `needs-human`
ticket that asks you to paste it again.

The agent also improves CI, this script and the other parts of the system by itself (`improve` skill). For settings
that only you can change (the environment, the network, the scheduled task, GitHub), it opens a `needs-human`
ticket with numbered steps.

## CI and Actions minutes

The repository is private, so GitHub Actions has 2,000 free minutes per month, and each job counts as at least
1 minute. On 2026-10-25, CI on each PR and the event workflows used about 900 minutes in one hour. Your decision:
PRs have no GitHub CI. Each run checks its PR in its own cloud session (lint, tests, Minecraft tests when needed)
and merges it. GitHub runs the full CI once a night on `main`. A red night run opens a `P0` ticket, and each run
also tests `main` when it starts. The dashboard, coverage and claim workflows run on a schedule (each run also
updates the dashboard). To get CI on each PR again: make the repository public (free minutes) or set a budget.
To pause all scheduled workflows (for example when the free minutes are used up), set the repository variable
`PAUSE_SCHEDULES` to `true` (Settings → Secrets and variables → Actions → Variables). A skipped job uses no
minutes, and a start by hand still runs. The agents set it on 2026-10-25 and delete it on 2026-11-01 (the reset).

## Files that steer the agent

| File | Content |
|---|---|
| `CLAUDE.md` | Project guide and rules. Every session reads it. |
| `docs/LEARNINGS.md` | What the agent learned. It updates this file itself. |
| `docs/ROADMAP.md` | Phases and goals of the project. |
| `.claude/skills/autopilot/` | The work cycle. |
| `.claude/skills/verify/` | How to test a change. |
| `.claude/skills/ticket/` | How to write and split tickets. |
| `.claude/skills/improve/` | How the agent measures and improves its own process. |

You can edit these files. The agent follows the version on `main`.
