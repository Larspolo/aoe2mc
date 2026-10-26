---
name: ticket
description: Write, size and split GitHub issues (tickets) for aoe2mc in the project format. Use when you make a new ticket, triage an owner's issue, or split a size-L ticket into sub-issues.
---

# Write a ticket

Tickets are GitHub Issues in `Larspolo/aoe2mc`. Write in ASD-STE100 Simplified Technical English.

## Form

Title: an instruction, less than 70 characters ("Fix the road pass on the sea floor").

Body:

```
## Goal
<One or two sentences: what changes for the user or the developer.>

## Context
<Where in the code: the files and functions that the ticket will change, in backticks (`buildings.py`, `furnish()`),
 why, and the evidence (output, image, test).
 The Minecraft feature that does the job (CLAUDE.md: "Minecraft features first"), or why there is none.>

## Acceptance criteria
- [ ] <A result that a test or a check can show.>
- [ ] <...>

## Verify
<The verify level (1-4) and the commands or checks.>

Depends on: #<n>, #<m>        (only when another ticket must close first)
Start after: <YYYY-MM-DD HH:MM> UTC   (only when the ticket must wait for a time, for example to measure 24 hours)
```

Labels: one priority (`P0`-`P3`), one kind (`bug`, `feature`, `tooling`, `design`, `docs`, `cleanup`),
one size (`size:S`, `size:M`, `size:L`). Add `needs-human` when only the owner can do it.

`dashboard.py --next` puts the tickets that share fewer files and functions with the work in progress first (#487):
name each file and function that the ticket changes, and no others (tools that only check, such as `render.py`, do not count).

## Size

- `size:S`: one PR, a small diff (about 150 lines or less), clear solution.
- `size:M`: one PR, up to about 400 lines, or one design decision.
- `size:L`: more than one PR, or research first. Do not start an L ticket: split it.

## Split an L ticket

1. Make S or M sub-issues (`sub_issue_write` in a cloud session, or "Depends on" lines in a local session).
   Make the first sub-issue small and useful alone.
2. Give the sub-issues the priority of the parent and the order of the work (lower number = first).
3. Add `epic` to the parent. The parent closes when all sub-issues are closed.

## needs-human tickets

The owner reads them on a phone. Give numbered steps, the exact names of settings or files, and what the
owner must reply. One ticket per decision.

A check ticket ("check X in the game") starts without `needs-human`: an agent runs the check first (`verify`, level 4),
comments the results and screenshots, and then adds `needs-human` with the list of what only a person can check (#580).

A research result that waits for the owner (options, milestones, "the owner decides") gets a `needs-human` ticket
for each decision, with the options and your recommendation, before the research ticket closes. A decision that
is only in a document is lost: milestones 2 and 3 of the replay research (#31) waited without a ticket until the owner asked (#371).

## Rules

- One goal per ticket. If you write "and also", make two tickets.
- Search the open issues first. Do not make a duplicate.
- Do not change the priority of a ticket that the owner set. Propose the change in a comment.
