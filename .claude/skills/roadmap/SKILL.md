---
name: roadmap
description: Turn the three goals of aoe2mc (convert maps, play AoE2 in Minecraft, replay a recorded game) into epics. Use in the queue refill (autopilot step 5) when the open epics have no work left, and when `python3 tools/claim.py 0 --roadmap` gives the roadmap review to the run (once per 100 merged PRs) to review the feature list in docs/ROADMAP.md.
---

# Plan toward the goals

`docs/ROADMAP.md` lists the features of each goal: done (`[x]`) or missing (`[ ]`, with a key such as `play:health`).
Owner decisions (2026-10-26): the agents make the epics themselves, a new epic starts at `P3`, and the goals take turns.

## Make the next epic (in the refill)

Do this in the refill of autopilot step 5 (you hold its lock, `python3 tools/claim.py 0 --refill`), when the open
epics have no goal left that an agent can do.

1. List the epics: `gh api "repos/OWNER/NAME/issues?labels=epic&state=all&per_page=100"` (`repo` in `agent.toml`). A feature has an
   epic when an epic body names its key ("Roadmap: `<key>`") or the roadmap line names an epic number. A `muted` epic
   counts too: do not make a second epic for its feature, and do not give it sub-issues.
2. Pick the goal: the goal whose newest epic is the oldest (the lowest issue number of the newest epics of the
   three goals; a goal without an epic first). Tie: the order of the file. Goal 4 (the agent system) takes no turn:
   its epics come from the `improve` skill and the owner.
3. In that goal, take the first missing feature without an epic.
4. Make the epic with the `ticket` skill: the title is an instruction, the body has the goal (what the player sees),
   the acceptance criteria (with a check that the whole feature is covered: `ticket` skill, "Split an L ticket"),
   the Minecraft feature that does the job (CLAUDE.md), the line "Roadmap: `<key>`", and
   the labels `epic`, `feature`, `size:L`, `P3`.
   When the feature has two or more good ways with no single best one (the interface, a game rule), make a decision
   ticket first (`ticket` skill, "Decision tickets") and let the sub-issues that need it depend on it.
5. Make its first 3–5 sub-issues (`size:S` or `size:M`, `P3`, `sub_issue_write`). The first one is small and useful
   alone. Name the files and functions that each one changes.
6. Do not change `docs/ROADMAP.md` for a new epic: the key in the epic body is enough (no merge conflicts).

## Release checks (`docs/RELEASE.md`, owner decision #878)

Do not change the order of the work for the release bar: the priority labels alone decide it. Look at the bar in the
roadmap review (below).
When all features of a milestone (B, A or C) of a goal are done (`python3 tools/release.py`: 0 features left in that
milestone), make each release check of the goal that has no ticket yet as a check ticket ("Check X in the game",
`ticket` skill, level 4 of `verify`), at the priority of the goal's epics, and write its number in the `ticket`
column of `docs/RELEASE.md`.
The trigger: the section "Release checks (no ticket, make them in the refill)" of `python3 tools/cycle_start.py`
(`release.due()`, #3342) lists these checks at each run start. A deep run makes their tickets in step 5 (`queue.md`).

## Review the feature list (the roadmap review)

When `python3 tools/claim.py 0 --roadmap` exits 0 (one run after each 100 merged PRs, #898, #2039), after step 8 of the autopilot skill:

1. Mark a feature done (`[x]`, with the epic number) when its epic is closed.
2. Compare each goal with AoE2 DE and with the code: what does a player see or do in AoE2 that the converter, the
   game program or the replay cannot do yet? Add at most 5 missing features, each with a new key and one line.
3. Keep the order: the features that the next features need come first.
4. Give each new feature a row in `docs/RELEASE.md` (milestone C, unless the owner says otherwise), and correct the
   estimates there: a feature whose epic has more sub-issues than its estimate needs no estimate.
5. Put the change into the PR of your ticket. The owner can change the list at any time.
