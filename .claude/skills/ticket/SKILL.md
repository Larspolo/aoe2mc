---
name: ticket
description: Write, size and split GitHub issues (tickets) for aoe2mc in the project format. Use when you make a new ticket, triage an owner's issue, or split a size-L ticket into sub-issues.
---

# Write a ticket

Tickets are GitHub Issues in the repository `repo` of `agent.toml`. Write in ASD-STE100 Simplified Technical English.

## Form

Title: an instruction, less than 70 characters ("Fix the road pass on the sea floor").

Body:

```
## Goal
<One or two sentences: what changes for the user or the developer.>

## Context
<Where in the code: the files and functions that the ticket will change, in backticks (`buildings.py`, `furnish()`),
 why, and the evidence (output, image, test).
 The platform feature that does the job (CLAUDE.md: the platform features first), or why there is none.>

## Acceptance criteria
- [ ] <A result that a test or a check can show.>
- [ ] <...>

## Verify
<The verify level (1-4) and the commands or checks.>

Depends on: #<n>, #<m>        (only when another ticket must close first)
Start after: <N> PRs after #<M>       (only when the ticket must wait for work, for example to measure a change: N merged PRs after PR #M)
Start after: <YYYY-MM-DD HH:MM> UTC   (only when the ticket must wait for a real time; the speed of the project changes, #2039)
```

A new line of a data file in `game/data/` needs no criterion "the values are those of the source" and no test of its values:
`tests/test_data_files.py` checks the form of each line (#1916). Name a test of behavior: a fight, a menu, a bonus that
the code computes.

Labels: one priority (`P0`-`P3`), one kind (`bug`, `feature`, `tooling`, `design`, `docs`, `cleanup`),
one size (`size:S`, `size:M`, `size:L`). Add `needs-human` when only the owner can do it.
A ticket that changes the agent system (skills, `CLAUDE.md`, the agent tools in `tools/`, workflows, the setup) also
gets `process` (#901): the dashboard counts the merged PRs with it.

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
3. Add `epic` to the parent. Its acceptance criteria check that the whole goal is covered, not only the sub-issues
   (owner rule, 2026-10-26, #820): name the full scope (a list, a table, or a source such as a wiki of the original) and a check
   that each item of it works, or that the owner excluded it in a comment on the epic. "All sub-issues are closed" is
   never the only criterion; it can be an extra line. Example: "Each code of the list on the wiki works in the
   program, or the owner excluded it." The epic closes when all its criteria are met.

## needs-human tickets

The owner reads them on a phone. Give numbered steps, the exact names of settings or files, and what the
owner must reply. One ticket per decision.
Each `needs-human` ticket (also when you add the label to an existing ticket: add the section to the body or to
your comment) has a section `## For the owner`, so that the `human` skill (`/human` on the owner's computer, #983)
can prepare and guide it:

    ## For the owner
    Kind: play            (or decision, setting, outside, close, question)
    World: <the command that makes the test data, from CLAUDE.md>
    Start: <the command that starts the program, from CLAUDE.md>
    1. <one step that the owner does>
    2. ...
    Reply: <what the owner must write on the ticket>

Leave out `World` and `Start` when the ticket needs no world.
A check of a live replay gives one line per moment that the owner watches, and one per task without a time;
the `human` skill gives them to `game/watch.py` (#1123). The place is `chopper`, `unit:NAME`, `building:NAME` or
`tile:X,Y`; `end` is the end of the replay:

    Watch: 3:00 | chopper | Do the walk, the turn to the tree and the particles look right?
    Task: Right click the ender pearl, then click a jump in the menu | Is the wait with "Jump to ..." acceptable?
    Watch: end | building:TOWN_CENTER | Is the end clear?

A check ticket ("check X in the game") starts without `needs-human`: an agent runs the check first (`verify`, level 4),
comments the results and screenshots with the list of what only a person can check (#580, #1707): sound, the feel of a control (delay, how hard it is to aim), "is it fun".
The agent judges the clicks (`mc_shot.Client`) and the look (screenshot next to the image of the original) itself; a look point
goes to the owner only when the agent cannot decide, with the reason (`verify`, level 5).
Then it closes the ticket on this evidence with the label `owner-sample` (owner decision B, #1708), not `needs-human`.
No owner point for times, speeds, values or texts: the agent measures them against the original (#1159). A look point links an
image before and an image after.
When the check finds bugs, the check ticket depends on the bug tickets and closes only after a check without bugs (#668).

## Decision tickets

Owner rule (2026-10-26): when a design has two or more clear options and no single best one (an interface, a game rule,
the order of features), the owner decides on GitHub. Do not choose, and do not ask only in a session.
- Title: "Decide: <the question>". Labels: `needs-human`, the kind of the work (`feature`, `design`, ...), `size:S`,
  the priority of the work that waits for it.
- Body: the question, the options as a table (what the player sees, plus, minus, cost), your recommendation and why,
  and "Reply with the option name (A, B, ...) or your own idea." Compare each option with `docs/PRINCIPLES.md` first, and
  name the principle that the recommendation follows ("follows P3"). When two principles give different options, say so.
- The tickets that need the answer get "Depends on: #<decision>", so no run starts them before the owner answers.
- When the owner answers: write the decision into the document of the topic (for example `docs/research/gameplay.md`),
  add its line to the end of `docs/DECISIONS.md` (`taken`, `changed` or `other`, and the principle), remove `needs-human`
  and close the decision ticket. When the answer follows no principle, or goes against one, say it in the comment that
  records the decision: "This does not follow P<n> (<rule>). I will add it as an exception; reply if P<n> must change."
  Do not add `needs-human` for this: the owner replies only when the principle must change.
- One clearly best option: no decision ticket. Choose it and say why in the PR.

A research result that waits for the owner (options, milestones, "the owner decides") gets a `needs-human` ticket
for each decision, with the options and your recommendation, before the research ticket closes. A decision that
is only in a document is lost: milestones 2 and 3 of the replay research (#31) waited without a ticket until the owner asked (#371).

## Model lanes

A cheap Haiku run takes the tickets with the label `lane:haiku` (#1715). Add it to each `size:S` ticket that names the
place of its change (a file, a function or a data line) and needs no look at a render, a screenshot or the real game.
Judge the other tickets one by one: there is no quota of Haiku tickets.
- Haiku does well: a clear goal and a clear end, a change at a known place (the body names the files or the
  function to change), a pattern that the code already has, values that the body gives or that a data file or a
  merged PR shows. Size S or a small M. Tests and a slow test run are fine.
- Opus does better: open design questions, a look to judge (renders, screenshots), a bug with an unknown cause,
  changes across many modules, checks in the real platform (server, client), process, decision, check and epic tickets.
  On hard coding tests Haiku 5.5 is far below Opus 5.5 (SWE-bench Pro about 65 % against 90 %), on clear tasks near it.
- Measured here (#1717): Haiku runs merged 9 of 9 PRs, take about 2.4 times as long (34 min against 14 min) and use
  a small part of the quota of an Opus run (`weights` in `python3 tools/usage.py --fire`).
- Measured on 2026-10-28: 22 PRs of 24 Haiku tickets. At API prices a Haiku ticket costs about 1/8 of an Opus
  ticket, and about 1/25 while its prompt stays below 100k tokens (one Haiku ticket: $0.07, Opus: $1.70 to $2.10).
When you are not sure, add it (owner, 2026-10-28): a Haiku run that finds the ticket unclear removes the label
(`autopilot` skill, `queue.md`), and then an Opus run takes it. The Haiku try costs little next to an Opus ticket.
A deep run (Opus at the default effort, about 4.5 times the tokens of a main run at low effort) takes the tickets with
`lane:deep` (owner, 2026-10-28). Add it when a wrong thought costs more than the lane: a bug whose cause the body does
not name, a change across three or more modules or a new structure, a process, decision, epic or `size:L` ticket, and a
ticket that failed before (red CI after 3 tries, a takeover, a reopened ticket). Aim at about 10 to 20 % of the tickets.
Never both `lane:haiku` and `lane:deep`.
While `reserved` in `[pacing]` of `agent.toml` names the lane, Opus runs never take its tickets (#1994).

## Rules

- One goal per ticket. If you write "and also", make two tickets.
- Search the open issues first. Do not make a duplicate.
- Do not change the priority of a ticket that the owner set. Propose the change in a comment.
- A ticket that uses a tool, file or function of a ticket that is not merged yet gets "Depends on: #<that ticket>": else it is a candidate at once, and a run claims it without the tool (#829 needed `tools/replay_drift.py` of the open PR #830).
- A ticket that adds an item to the menu of a building (`train.ITEMS`) names its slot: the first free slot of that
  building after the slots of `main` and of the open tickets of the same building. Two tickets that said "a free slot"
  took the same slot and broke main twice in one hour (#1551: slot 18 of the archery range; #1548 and #1549: slot 20 of
  the university).
