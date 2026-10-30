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
Do not ask the owner about times, speeds, values or texts: an agent measures them (#1159). When a point of the ticket
asks for one, measure it in this session and write the result. A look comparison: show the image before first.
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
`aoe2mc.py`, `game/run.py`, `framework/tools/owner_tasks.py`): the Bash tool does not keep `source .venv/bin/activate` between
two calls. Tell the owner to type `source .venv/bin/activate` in each new terminal.

## 2. Sort the tickets and make one plan

Run `python3 framework/tools/owner_tasks.py`. It prints the open `needs-human` tickets that are not muted, decision tickets
first, then the oldest first, each with its kind and its question. With no ticket: say so and offer "Wait for the
next ticket" (below); if the owner does not want to wait, stop.

Check each ticket: is the owner really needed (#1674)? Read its body and its last comments, and sort it into one group:
1. **Close now**: the work is done and only the close is open (a denied close, #862, or an owner answer that only
   needs a close). Close it as completed with an evidence comment (what proves each criterion), then tell the owner.
2. **Agent work**: the point asks for times, speeds, values or texts (#1159), or tests and agent checks cover it
   already. Measure it in this session, or remove `needs-human` with a comment that names the evidence.
3. **Owner needed**: sound, the feel of a control, "is it fun", a look that the agent could not decide (it says why,
   #1707), a decision or a setting. Clicks and a look next to the AoE2 image are agent work (`verify`, level 5).

Then run `python3 framework/tools/owner_tasks.py --plan`: it puts each ticket into "close now", "replay", "play game" or
"no game". Move the tickets of group 2 out, and show the plan to the owner: one replay with `game/watch.py` for all
replay tickets (one stage list), one play game with `game/play_guide.py` for all play tickets (one step file), then
the decisions and settings. Ask with `AskUserQuestion` whether to start the plan, or which single ticket to do.

The play game (step 3, "play"): `python3 tools/scenarios.py owner_loop out/loop.aoe2scenario` makes the play-test
map (a town, a barracks, a lake with a dock, a transport ship and 3 militia, the bot with 5 militia toward the town
center). Write one step file (JSON, see the docstring of `game/play_guide.py`: setup commands with `{BARRACKS}`,
`{MILITIA1}` ..., the task, the question for each ticket), start `python3 game/run.py out/LoopWorld --play --bot --bot-attack 3:00` (an early attack for the arrows)
(add `--cheats` when a step needs them), and when the server says "Join the server localhost:PORT", start
`python3 game/play_guide.py PORT out/LoopWorld STEPS.json --out out/play.json` in the background. Wait for its JOINED,
ASK, ANSWER and DONE lines; the answers are in `out/play.json`. Write each answer on its ticket (step 5).

Pitfalls of the session of #1674 (avoid them):
- Give each step the state that it needs with its setup commands (age, resources), or with the key `cheats` (a list of
  cheat codes, for example `["aegis", "robin hood"]`: the guide runs them for the owner, #2052; start `game/run.py`
  with `--cheats`): a Stone Wall and a Gate need the Feudal Age (`build.AGE`).
- A step that needs an attack on a building has no own units between the enemy and the building: the bot attacks the
  nearest unit (`bot.fight`). In `owner_loop` the villagers at the town center are the nearest.
- `game/run.py --replay` without `game/watch.py` starts at once and ends before the owner joins: use `game/watch.py`.
- The owner can answer in two chat lines: `game/play_guide.py` takes the lines of 20 s as one answer.
- macOS: the first start of a downloaded app or JDK can need System Settings → Privacy & Security → "Open Anyway" (#1668).

Sample check (owner decision B, #1708): agents close check tickets on their evidence with the label `owner-sample`.
Run `python3 framework/tools/owner_tasks.py --sample` and offer some of these tickets (the oldest first) as one more play game or
replay, with the owner points of their last agent comment. A finding becomes a bug ticket (step 5). Remove
`owner-sample` from each ticket that the owner checked, also without a finding.

Wait for the next ticket (#1025): start `python3 framework/tools/owner_tasks.py --wait` with `run_in_background` and end the
turn. While it waits, the session uses no model turn (one GitHub request each 5 minutes, at most 12 hours). Exit 0:
it printed the new ticket in the format of the list: show it and ask the owner with `AskUserQuestion` whether to do
it now (step 3). Exit 1 ("No new ticket in 12 hours."): say so and offer to wait again.

## 3. Prepare the chosen ticket

Run `python3 framework/tools/owner_tasks.py --show N`. It prints the section `## For the owner` of the ticket (the `ticket`
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
  4. A replay ticket with `Watch:` lines (the owner watches moments of a live replay, #1123): start the guide instead,
     in the background: `python3 game/watch.py out/World --watch FILE --speed 4 --out out/watch.json` (FILE: the
     ticket body or a JSON list of stages, see the docstring of `game/watch.py`). It plays to 5 real seconds before
     each moment, pauses, teleports the owner to the place when the owner joins, plays the moment at speed 1 and asks
     the question in the chat. Wait for its `READY`, `JOINED`, `ASK`, `ANSWER` and `DONE` lines with a loop and a
     counter (macOS has no `timeout`), and tell the owner what comes next. The answers are in `out/watch.json`.
- **decision**: show the options table of the ticket and the agent's recommendation. Ask with `AskUserQuestion`:
  one option per row (A, B, ...), the recommended one first with "(recommended)". The owner can also type an own idea.
- **setting** (environment, network, variables, scheduled task, GitHub settings): give the exact place (the page and
  the field) and the exact text to paste, from the ticket. Never read or print a secret.
- **outside** (a step outside the cloud, for example a second repository): do the steps of the ticket in this
  session after the owner agrees to each step that writes outside the clone.
- **close**: show the evidence of the agent's last comment. When the owner agrees, close the issue as completed
  (`gh issue close N --reason completed`, or the GitHub MCP tools) and make the follow-up change that the comment names
  (for example a line of `steering/project/ROADMAP.md`) on a branch with a PR.
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
   End the comment with the footer of `framework/tools/dashboard.py` (`FOOTER`).
2. For each problem: a bug ticket with the `ticket` skill, and "Depends on: #bug" on the check ticket, so that a run
   checks again after the fix (#668). Do not fix it in this session unless the owner asks.
3. Remove `needs-human` when the answer is complete. For a decision: write the decision into the document of the
   topic and close the decision ticket (`ticket` skill, "Decision tickets"). Keep `needs-human` and say what is open
   when the answer is not complete.
4. Stop the server (Ctrl-C in `game/run.py`) and offer the next ticket of the list (step 2). After the last ticket:
   offer "Wait for the next ticket" (step 2).
