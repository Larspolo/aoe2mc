---
name: roadmap
description: Turn the three goals of aoe2mc (convert maps, play AoE2 in Minecraft, replay a recorded game) into epics. Use in the queue refill (autopilot step 5) when the open epics have no work left, and when `python3 framework/tools/claim.py 0 --roadmap` gives the roadmap review to the run (once per 100 merged PRs) to review the feature list in steering/project/ROADMAP.md.
---

# Plan toward the goals

`steering/project/ROADMAP.md` lists the features of each goal: done (`[x]`) or missing (`[ ]`, with a key such as `play:health`).
Owner decisions (2026-10-26): the agents make the epics themselves, a new epic starts at `P3`, and the goals take turns.

## Make the next epic (in the refill)

Do this in the refill of autopilot step 5 (you hold its lock, `python3 framework/tools/claim.py 0 --refill`), when the open
epics have no goal left that an agent can do.

1. List the epics: `gh api "repos/OWNER/NAME/issues?labels=epic&state=all&per_page=100"` (`repo` in `agent.toml`), and the same with `&page=2` (more than 100 epics since 2026-10-29; `--paginate` stops after page 1, `autopilot/github.md`). A feature has an
   epic when an epic body names its key ("Roadmap: `<key>`") or the roadmap line names an epic number. A `muted` epic
   counts too: do not make a second epic for its feature, and do not give it sub-issues. A plain ticket that names the
   key (an owner request, `play:farm-reseed` in #3283) does not count: grep the open and the closed issues of the last day
   for the key and the topic, and make tickets only for the parts that it leaves out (#3422, #3423).
2. Pick the goal: the goal whose newest epic is the oldest (the lowest issue number of the newest epics of the
   three goals; a goal without an epic first). Tie: the order of the file. Goal 4 (the agent system) takes no turn:
   its epics come from the `improve` skill and the owner.
3. In that goal, take the first missing feature without an epic inside the release focus
   (`steering/project/RELEASE.md`, "Release focus": `python3 tools/release.py` names the features that wait; a feature
   with no row is level C). Make no epic for a feature that waits: no goal has one, make no epic. Skip a feature
   whose line names an open `after-release` or `muted` ticket: the owner holds it (`usage.held`, #5301). Grep the code for it first: a ticket can do a
   feature with no epic (`play:taunts` by #3318). Then mark it `[x]` with the ticket in the next PR, and take the next one.
4. Make the epic with the `ticket` skill: the title is an instruction, the body has the goal (what the player sees),
   the acceptance criteria (with a check that the whole feature is covered: `ticket` skill, "Split an L ticket"),
   the Minecraft feature that does the job (CLAUDE.md), the line "Roadmap: `<key>`", and
   the labels `epic`, `feature`, `size:L`, `P3`.
   When the feature has two or more good ways with no single best one (the interface, a game rule), make a decision
   ticket first (`ticket` skill, "Decision tickets") and let the sub-issues that need it depend on it.
5. Make its first 3–5 sub-issues (`size:S` or `size:M`, `P3`, `gh api .../sub_issues`: `ticket` skill). The first one is small and useful
   alone. Name the files and functions that each one changes.
6. Do not change `steering/project/ROADMAP.md` for a new epic: the key in the epic body is enough (no merge conflicts).

## Release cycle (after a release, `steering/project/RELEASE.md`)

Do this first in the refill when open issues have the label `rank` (the pacer starts a deep run for them:
"rank N tickets after the release"). Lock it: `python3 framework/tools/claim.py 0 --refill`.

1. List the `rank` tickets (also epics) and the new release epic "Release vX.Y.Z" (labels `release`, `rank`).
2. Rank the tickets against each other, not one by one: the benefit for a play tester and a player of the release
   first (P9: what the player sees and does), then the size (smaller first), then the order of the roadmap. Write the
   ranked list in a comment on the release epic, one line per ticket with a short reason.
3. Give the first third `P1`, the next third `P2`, the rest `P3` (replace the old priority label; not of a ticket whose
   priority the owner set after its creation: keep it). A ticket that must not come back now gets `muted` and a
   one-line reason (owner, 2026-11-01): the owner brings it back.
4. Give each ranked ticket that is not muted the milestone of the new release ("vX.Y.Z": `issue_write` with
   `milestone`, or `gh api repos/OWNER/NAME/issues/N -X PATCH -F milestone=M`; also epics and their open sub-issues).
   Write the acceptance criteria into the body of the release epic: the milestone has no open issue, no open bug
   `P0` or `P1`, and a play-test check (`tools/play_check.py`: a full game against the bot, no server error, no stuck unit).
5. Look at the waiting roadmap features (`python3 tools/release.py`): a feature that the ranking puts into the next
   release gets level `A` in its row of `steering/project/RELEASE.md` (a `docs` PR). Correct the kinds list of
   "Release focus" when the ranking shows a new kind.
6. Remove `rank` from each ticket and from the epic. Then do the other refill steps.

## Release checks (`steering/project/RELEASE.md`, owner decision #878)

Inside the release focus (`steering/project/RELEASE.md`), the priority labels decide the order of the work; the work
outside it waits with `after-release`. Look at the bar in the
roadmap review (below).
When all features of a level (B, A or C) of a goal are done (`python3 tools/release.py`: 0 features left in that
level), make each release check of the goal that has no ticket yet as a check ticket ("Check X in the game",
`ticket` skill, level 4 of `verify`), at the priority of the goal's epics, and write its number in the `ticket`
column of `steering/project/RELEASE.md`.
The trigger: the section "Release checks (no ticket, make them in the refill)" of `python3 framework/tools/cycle_start.py`
(`release.due()`, #3342) lists these checks at each run start. A deep run makes their tickets in step 5 (`queue.md`).

## Review the feature list (the roadmap review)

When `python3 framework/tools/claim.py 0 --roadmap` exits 0 (one run after each 100 merged PRs, #898, #2039; after 30 while the refill has
no source: R < N, each feature has an epic, no fallback, `claim.ROADMAP_EARLY`, #3741; then also after 60 minutes with
no merged PR, at the merged count, at least 1: `claim.ROADMAP_IDLE`), after step 8 of the autopilot skill:

1. Mark a feature done (`[x]`, with the epic number) when its epic is closed.
   Add a line for each epic key ("Roadmap: `<key>`") that the list does not have: `tools/release.py` counts only
   the keys of the list (#4268: `play:unique-techs` of #4096 with 34 sub-issues was not counted).
2. Compare each goal with AoE2 DE and with the code: what does a player see or do in AoE2 that the converter, the
   game program or the replay cannot do yet? Add at most 5 missing features, each with a new key and one line.
   Before you add one, grep the open issues for its topic (all tickets, also `after-release` and `muted`, not only
   epics): a ticket that covers it goes into the line as `(#N)` (#5290: #4198 of the owner held the export).
3. Keep the order: the features that the next features need come first.
4. Give each new feature a row in `steering/project/RELEASE.md` (level C, unless the owner says otherwise: it waits
   for the release, "Release focus"), and correct the
   estimates there. Do not remove an estimate: `release.py` takes the larger of the estimate and the sub-issues of
   the epic, and with no estimate the median of the closed epics, more than a small epic has (#3678: 20 tickets).
5. Put the change into the PR of your ticket. A run with no ticket (a deep run after an empty refill) makes a
   `docs`, `size:S` ticket for the review, claims it and ships it (#4600). The owner can change the list at any time.
