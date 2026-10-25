# Steering the agent

The agent (Claude Code) works on this project automatically. You steer it asynchronously through GitHub
Issues. You can do all of this in the GitHub app on your phone.

## How the agent works

Each run does one work cycle (the `autopilot` skill):

1. It reads your new comments on issues and PRs, and does what they ask.
2. It sorts new issues: priority, kind and size labels. It splits large tickets.
3. It does the top ticket: code, tests, a PR. It merges the PR when CI passes.
4. It reports on the **Agent status** issue (label `agent-status`): it updates the dashboard in the issue
   body and adds a short comment. GitHub sends you a notification.
5. It improves its own process: it writes learnings, corrects its instructions and makes tooling tickets.

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
- **On your computer**: `scripts/autopilot.sh 3` runs 3 cycles, one ticket each.
  It needs the Claude Code CLI and the GitHub CLI (`gh auth login`).
- **By hand**: open a Claude Code session in this repository and type `/autopilot`.

## Network for Minecraft tests

The cloud network blocks the Mojang servers. To let the agent start a headless Minecraft server for tests,
add these hosts to the environment: open the cloud environment menu in the session title bar → Edit →
Network access → Allowed domains:

    piston-meta.mojang.com
    piston-data.mojang.com
    libraries.minecraft.net

Keep "Allow package managers" on. Steps: https://code.claude.com/docs/en/cloud-environments#network-access

## Files that steer the agent

| File | Content |
|---|---|
| `CLAUDE.md` | Project guide and rules. Every session reads it. |
| `docs/LEARNINGS.md` | What the agent learned. It updates this file itself. |
| `docs/ROADMAP.md` | Phases and goals of the project. |
| `.claude/skills/autopilot/` | The work cycle. |
| `.claude/skills/verify/` | How to test a change. |
| `.claude/skills/ticket/` | How to write and split tickets. |

You can edit these files. The agent follows the version on `main`.
