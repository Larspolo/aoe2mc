# Release bar

The owner decision of #878 (2026-10-26): a goal is at 100 % when all its features of `docs/ROADMAP.md` are done
(milestone C), its release checks pass and its bug reserve is used. The milestones B (a smaller first test) and A
(the core) are indications only: the priority labels alone decide the order of the work.
`python3 tools/release.py` prints the progress of each goal and milestone.

Bug reserve: 0.3

## Rules

1. A row names a feature of `docs/ROADMAP.md` by its key, or a release check by an id that ends in `-check-...`.
   A roadmap feature without a row is milestone C. Give each new roadmap feature a row (`roadmap` skill).
2. The epics of a feature: an epic whose body has the line ``Roadmap: `key` ``, and the epics that its roadmap line
   names (`#N`).
3. Default estimate = the median number of sub-issues of the closed epics with sub-issues.
4. Status of a feature: In progress when one of its epics is open; else Done when it has an epic or its roadmap line
   is checked (`[x]`); else To do.
5. Tickets of a feature: done = the closed sub-issues of its epics (at least 1 when it has an epic); a checked feature
   without an epic counts the default estimate as done. Left = 0 when Done, else max(all sub-issues of its epics,
   estimate or default) − closed sub-issues.
6. A release check: left = its estimate until its check ticket closes, then done = its estimate.
7. Bug reserve of a milestone = ceil(0.3 × the feature tickets left of that milestone).
8. Progress = done ÷ (done + left). B counts the B features, A the B and A features, C all features. Each milestone
   counts all release checks of the goal and its own reserve.

## Convert maps

| id | milestone | estimate | check | ticket |
|---|---|---|---|---|
| `convert:terrain` | B | | | |
| `convert:designs` | B | | | |
| `convert:units` | B | | | |
| `convert:inputs` | B | | | |
| `convert:version` | B | | | |
| `convert:texts` | B | | | |
| `convert:sounds` | B | | | |
| `convert:triggers` | B | | | |
| `convert:large` | B | | | |
| `convert:minimap` | A | | | |
| `convert-check-maps` | B | 5 | A test set of 20 real maps (the ranked map pool, 3 campaigns, 2 old .scx scenarios) converts with no error, no unit in a block and no load error on a server | |
| `convert-check-look` | B | 3 | A person checks the screenshots of the test set; the fixes of what they find | |
| `convert-check-speed` | B | 1 | A 480 × 480 map converts in less than 10 minutes and 8 GB | |

## Play AoE2

| id | milestone | estimate | check | ticket |
|---|---|---|---|---|
| `play:program` | B | | | |
| `play:gather` | B | | | |
| `play:build` | B | | | |
| `play:fight` | B | | | |
| `play:train` | B | | | |
| `play:bot` | B | 10 | | |
| `play:scale` | B | 5 | | |
| `play:menu` | B | | | |
| `play:health` | B | | | |
| `play:military-train` | B | | | |
| `play:tech` | A | 8 | | |
| `play:ages` | A | 6 | | |
| `play:feedback` | B | | | |
| `play:control` | B | | | |
| `play:garrison` | B | | | |
| `play:win` | B | 3 | | |
| `play:walls` | A | 5 | | |
| `play:civs` | C | | | |
| `play:monks` | C | | | |
| `play:market` | C | | | |
| `play:two-players` | C | | | |
| `play:siege` | C | | | |
| `play:naval` | C | | | |
| `play:cheats` | C | | | |
| `play:fog` | C | | | |
| `play:save` | C | | | |
| `play-check-game` | B | 5 | An agent plays a full game against the bot with a script, from the Dark Age to a win or a loss (about 30 minutes): no server error, no stuck unit | |
| `play-check-speed` | B | 2 | With 200 units of each player, the server keeps 20 ticks per second | |
| `play-check-kit` | B | 2 | A play-test kit: how to start and join, the controls, how to report a bug | |
| `play-check-person` | B | 1 | A person plays one test game | |

## Replay a game

| id | milestone | estimate | check | ticket |
|---|---|---|---|---|
| `replay:start` | B | | | |
| `replay:live` | B | | | |
| `replay:units` | B | | | |
| `replay:versions` | B | | | |
| `replay:record` | B | | | |
| `replay:simulate` | B | | | |
| `replay:control` | B | | | |
| `replay:follow` | B | | | |
| `replay:view` | A | | | |
| `replay:score` | A | | | |
| `replay:effects` | C | | | |
| `replay:postgame` | C | | | |
| `replay-check-full` | B | 5 | A complex record (a team game of about 40 minutes with castles and large fights) replays from start to end with no error | |
| `replay-check-follow` | B | 3 | The position tool (#813) shows no stray unit and less than 5 % stuck units on that record | |
| `replay-check-speed` | B | 2 | The server keeps at least 18 ticks per second at speed 1 through the whole record | |
