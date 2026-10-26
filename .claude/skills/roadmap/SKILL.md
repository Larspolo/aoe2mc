---
name: roadmap
description: Turn the three goals of aoe2mc (convert maps, play AoE2 in Minecraft, replay a recorded game) into epics. Use in the queue refill (autopilot step 5) when the open epics have no work left, and every 10th run to review the feature list in docs/ROADMAP.md.
---

# Plan toward the goals

`docs/ROADMAP.md` lists the features of each goal: done (`[x]`) or missing (`[ ]`, with a key such as `play:health`).
Owner decisions (2026-10-26): the agents make the epics themselves, a new epic starts at `P3`, and the goals take turns.

## Make the next epic (in the refill)

Do this in the refill of autopilot step 5 (you hold its lock, `python3 tools/claim.py 0 --refill`), when the open
epics have no goal left that an agent can do.

1. List the epics: `gh api "repos/Larspolo/aoe2mc/issues?labels=epic&state=all&per_page=100"`. A feature has an
   epic when an epic body names its key ("Roadmap: `<key>`") or the roadmap line names an epic number.
2. Pick the goal: the goal whose newest epic is the oldest (the lowest issue number of the newest epics of the
   three goals; a goal without an epic first). Tie: the order of the file.
3. In that goal, take the first missing feature without an epic.
4. Make the epic with the `ticket` skill: the title is an instruction, the body has the goal (what the player sees),
   the acceptance criteria, the Minecraft feature that does the job (CLAUDE.md), the line "Roadmap: `<key>`", and
   the labels `epic`, `feature`, `size:L`, `P3`.
   When the feature has two or more good ways with no single best one (the interface, a game rule), make a decision
   ticket first (`ticket` skill, "Decision tickets") and let the sub-issues that need it depend on it.
5. Make its first 3–5 sub-issues (`size:S` or `size:M`, `P3`, `sub_issue_write`). The first one is small and useful
   alone. Name the files and functions that each one changes.
6. Do not change `docs/ROADMAP.md` for a new epic: the key in the epic body is enough (no merge conflicts).

## Review the feature list (every 10th run)

When `runs` (the agent state of the status issue) is a multiple of 10, after step 8 of the autopilot skill:

1. Mark a feature done (`[x]`, with the epic number) when its epic is closed.
2. Compare each goal with AoE2 DE and with the code: what does a player see or do in AoE2 that the converter, the
   game program or the replay cannot do yet? Add at most 5 missing features, each with a new key and one line.
3. Keep the order: the features that the next features need come first.
4. Put the change into the PR of your ticket. The owner can change the list at any time.
