---
name: human
description: Help the owner of aoe2mc with the tickets that wait for the owner (label needs-human). List them, prepare the chosen one on the owner's computer (world, server, options), guide the owner step by step and write the result on the ticket. Only for a local Claude Code session that the owner starts in a clone of the repository and types "/human" in. Runs cannot use it - the cloud has no window and no real input.
---

# Human: do the needs-human tickets with the owner

A `needs-human` ticket waits for what only a person can do: a play test with a real Minecraft client (a check ticket
after the agent check, #580, #668), a decision ("Decide: ..."), a setting of the environment or GitHub, a step outside
the cloud (#907), or a close that the auto mode did not let the agent do (#862). The owner's computer has a window
and real input. This skill does the setup, so that the owner only plays, looks and answers.
Write in ASD-STE100 (CLAUDE.md, "Language"). Talk to the owner in short steps: one step, then wait.
The project values (repository, owner, labels) are in `agent.toml`.

## 1. Check the computer

Run these checks. For each one that fails, say what is missing and give the install command. Continue only with
the checks that the chosen ticket needs (a decision needs only GitHub).

| Check | Command | Fix |
|---|---|---|
| Latest code | `git pull --ff-only origin main` | Commit or stash local changes first. |
| Python 3.10+ with the packages | `PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python; $PY -c "import numpy, nbtlib, PIL, AoE2ScenarioParser"` | `python3 -m pip install -r requirements-dev.txt`. When `pip` gives "externally-managed-environment" (Homebrew Python, PEP 668): `python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt` (#1044) |
| Java 25 (Paper server, plugin) | `java -version` | Install a JDK 25 (for example Eclipse Temurin 25). macOS: the owner types `brew install --cask temurin@25` in a terminal (the installer asks for the password with `sudo`). |
| Minecraft 26.3 | Ask the owner. | Minecraft launcher → Installations → New → version 26.3. |
| GitHub access | `gh auth status`, or the GitHub MCP tools | `gh auth login` |
| Commit email (a ticket with a PR, for example a close) | `git config user.email` ends with `@users.noreply.github.com`. GitHub refuses a push with a private email (#1020). | `git config user.email "$(gh api user --jq '"\(.id)+\(.login)@users.noreply.github.com"')"` (this clone only) |
| A `.aoe2record` file (replay tickets) | `python3 -c "import mgz"` (`.venv/bin/python` when it exists) | `python3 -m pip install mgz` (`.venv/bin/python -m pip install mgz` when `.venv` exists) |

When `.venv/bin/python` exists, use it in place of `python3` for each command of this skill (`tools/scenarios.py`,
`aoe2mc.py`, `game/run.py`, `tools/owner_tasks.py`): the Bash tool does not keep `source .venv/bin/activate` between
two calls. Tell the owner to type `source .venv/bin/activate` in each new terminal.

## 2. List the tickets

Run `python3 tools/owner_tasks.py`. It prints the open `needs-human` tickets that are not muted, decision tickets
first, then the oldest first, each with its kind and its question. Show the list and ask the owner which ticket to
do (`AskUserQuestion` with the first four tickets, plus "other"). With no ticket: say so and offer "Wait for the
next ticket" (below); if the owner does not want to wait, stop.

Wait for the next ticket (#1025): start `python3 tools/owner_tasks.py --wait` with `run_in_background` and end the
turn. While it waits, the session uses no model turn (one GitHub request each 5 minutes, at most 12 hours). Exit 0:
it printed the new ticket in the format of the list: show it and ask the owner with `AskUserQuestion` whether to do
it now (step 3). Exit 1 ("No new ticket in 12 hours."): say so and offer to wait again.

## 3. Prepare the chosen ticket

Run `python3 tools/owner_tasks.py --show N`. It prints the section `## For the owner` of the ticket (the `ticket`
skill asks for it), else the last request of the agent. Read the ticket body and its comments too. Then prepare by
the kind:

- **play** (a play test in Minecraft):
  1. Make the world with the command of the section, for example
     `python3 tools/scenarios.py village out/village.aoe2scenario` and
     `python3 aoe2mc.py out/village.aoe2scenario out/VillageWorld`. Put worlds in `out/` (ignored by git).
  2. Start the server in the background: `python3 game/run.py out/VillageWorld --play` (add `--cheats`, `--bot`,
     or `--replay --speed N` when the section says so). It builds the plugin the first time. Wait for the line
     "Join the server localhost:PORT" and give the owner that address.
  3. Tell the owner: start the Minecraft launcher with version 26.3 → Multiplayer → Direct Connection → paste the address.
- **decision**: show the options table of the ticket and the agent's recommendation. Ask with `AskUserQuestion`:
  one option per row (A, B, ...), the recommended one first with "(recommended)". The owner can also type an own idea.
- **setting** (environment, network, variables, scheduled task, GitHub settings): give the exact place (the page and
  the field) and the exact text to paste, from the ticket. Never read or print a secret.
- **outside** (a step outside the cloud, for example a second repository): do the steps of the ticket in this
  session after the owner agrees to each step that writes outside the clone.
- **close**: show the evidence of the agent's last comment. When the owner agrees, close the issue as completed
  (`gh issue close N --reason completed`, or the GitHub MCP tools) and make the follow-up change that the comment names
  (for example a line of `docs/ROADMAP.md`) on a branch with a PR.
- **question**: show the question and write down the owner's answer.

## 4. Guide

Give one numbered step at a time, and wait for the owner. Write down what the owner says and sees, in the owner's words.
For a play test, set up each step (time, units, resources) for the owner: `game/run.py` without `--play` or
`--replay` reads Minecraft commands on its input; with them, give the owner the exact command to paste in the chat
(the owner is an operator). When something goes wrong, look at `logs/latest.log`
of the server first.
Screenshots of the owner: ask for the file paths, then push them to `refs/heads/checks/N` as an orphan commit and link
`https://raw.githubusercontent.com/OWNER/NAME/checks/N/NAME.png` (`docs/LEARNINGS.md`, #614; for a second check build
the tree from the old tree, #718).

## 5. Report

1. Comment on the ticket in ASD-STE100: what the owner did, the owner's words quoted (`> ...`), the images, and the result.
   End the comment with the footer of `tools/dashboard.py` (`FOOTER`).
2. For each problem: a bug ticket with the `ticket` skill, and "Depends on: #bug" on the check ticket, so that a run
   checks again after the fix (#668). Do not fix it in this session unless the owner asks.
3. Remove `needs-human` when the answer is complete. For a decision: write the decision into the document of the
   topic and close the decision ticket (`ticket` skill, "Decision tickets"). Keep `needs-human` and say what is open
   when the answer is not complete.
4. Stop the server (Ctrl-C in `game/run.py`) and offer the next ticket of the list (step 2). After the last ticket:
   offer "Wait for the next ticket" (step 2).
