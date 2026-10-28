# Autopilot: triage of large tickets, epics and the queue refill

Read this file in step 4 when a ticket has `size:L`, in step 5 before the pick (the epic check, at most 3 epics),
when fewer tickets are ready than the target number of runs (the refill), and in a haiku lane run. Part of the `autopilot` skill (#1700).

## Haiku lane (step 5)

When the argument names `lane haiku` (the scheduled task "aoe2mc autopilot haiku"), run
`git config aoe2mc.lane haiku` first (the claims then tell the pacer that this run is cheap, #1727), pick only with
`python3 tools/dashboard.py --next --lane haiku`, skip the epic check, the queue refill, the roadmap review and the
process review, and stop when no `lane:haiku` ticket is ready. Do one ticket per run: stop after its report,
also with the argument `max` (a Haiku call costs 5 times more above 100k prompt tokens, and the Haiku runs
reached 91k to 200k; the pacer starts a fresh run with a 65k context for the next ticket, 2026-10-28). A ticket that is not as clear as its label says: release
the claim, remove `lane:haiku`, comment why in one line, and take the next one. Write the report with `tools/report.py` (`report.md`): it adds `· lane haiku` from the git config (#1982).

## Large tickets (step 4)

If the size is L, split it into S or M sub-issues with the `ticket` skill. Give the parent label `epic`.
If the top candidate of step 5 has `size:L`, split it now (`ticket` skill), then pick again.

## Epics and refill (step 5)

Epics first: an epic is never a candidate, so its rest of the work needs sub-issues. Before you claim a ticket, look
at the open epics (label `epic`, not `needs-human`, not `muted`, any priority) with no open sub-issue, at most 3 per run. The
priority does not matter here: a check of `P2` and `P3` epics was skipped, and six finished epics stayed open (#799).
For each one, read its acceptance criteria and all its comments. An owner comment after the last agent comment comes
first: handle it as in step 3 (lock, answer). Do not post a request that the epic already has (#820: two runs asked
the same thing, and no run answered the owner's question between them). An epic without a criterion that checks that the
whole goal is covered (owner rule, #820: never only "All sub-issues are closed") gets one first (`ticket` skill, "Split
an L ticket"). Check that criterion against the full scope (for "all X": the full list, for example a wiki of the original) and
name each missing item. Close the epic with a comment only when all criteria are met
(name the evidence for each, then the label `close`: `owner.md`, "Close an issue", #1740). Else lock the epic first: `python3 tools/claim.py E --refill`
(E = the epic; exit 1: another run makes its sub-issue, skip the epic, #505). Then make one sub-issue (same priority)
for the criteria that an agent can do. A criterion that needs the owner stays on the epic. Then pick again (#176, #155 waited while P3 tickets ran).
Refill the queue when fewer candidates are ready than the target number of runs, so that parallel runs always find
work: N = the target and R = the ready tickets of `python3 tools/usage.py --fire` (its stderr line). Refill only when
R < N, and make at most 2 × N − R tickets, so the queue stays at most twice the target (owner, #664: when fewer runs work
again, a large queue only waits). Do this at most once per run, in about 10 minutes.
Lock it first: `python3 tools/claim.py 0 --refill` (one run per 10 minutes). Exit 1: another run makes the whole
refill; then refill one open epic instead (the first one with open goals that an agent can do, under its lock below):
up to 10 sub-issues (within the cap) for its open goals, then pick again. The pacer starts `refill_runs` runs more
than the ready tickets for this (`agent.toml`): many runs close tickets faster than one refill makes them (#650;
2026-10-28: 3 ready tickets for 40 target runs). It starts them only while an open ticket is less than 60 minutes old
(`usage.refill_runs`), else 1: an empty refill run costs quota.
Give each new ticket `lane:haiku` when a Haiku run can do it as well as an Opus run (`ticket` skill, "Model lanes"):
judge each ticket, do not aim at a number.
Also lock each epic E with `python3 tools/claim.py E --refill` before you make its tickets (exit 1: skip that epic, #505).
A `muted` ticket or epic (the owner mutes it until later, 2026-10-26) is out of all these steps: no split, no check, no
new sub-issues, no `needs-human`. Still answer an owner comment on it (step 3).
1. Split each `size:L` ticket N without open sub-issues (`ticket` skill), also when it is not a candidate yet. Lock it
   first with `python3 tools/claim.py N --refill` (exit 1: skip it).
2. For each open epic whose sub-issues are all closed: make a sub-issue for each acceptance criterion that is
   still open and that an agent can do. A criterion that needs the owner stays on the epic.
3. Make up to 20 new tickets (within the cap) for the remaining goals of the open epics, and for the fallbacks in
   `docs/coverage.md`. When the open epics have no goal left that an agent can do, make the next epic from the
   feature list of `docs/ROADMAP.md` with the `roadmap` skill (the goals take turns). Priority: that of the epic, else `P3`. Never `P0` or `P1`, except for
   a `tooling` ticket that blocks other tickets. Look for duplicates first, and list the open issues again just
   before you make the tickets: parallel runs make the same follow-ups at the same time (#300, #301).
   Run that list in its own tool call and read it before the create calls: a list and the creates in one call made 7 copies (#2778).
   Read the gap lists from main, not from your branch (`git fetch origin main`, `git show
   origin/main:tests/data/civ_bonuses.jsonl`), and also list the issues closed in the last 2 hours: #2340 copied
   #2309, which merged while the branch was 20 minutes old, and #2306 copied the closed #2249.
4. Prefer tickets that depend on no open ticket and change other files than the claimed tickets (fewer conflicts).
5. An epic takes at most 100 sub-issues (GitHub: 422 "Parent cannot have more than 100 sub-issues", #2538): a new
   ticket of a full epic says "Part of #E" in its body only; name it in the refill comment on the epic.
