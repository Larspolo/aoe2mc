# Release bar

The owner decision of #878 (2026-10-26): a goal is at 100 % when all its features of `steering/project/ROADMAP.md` are done
(milestone C), its release checks pass and its bug reserve is used. The milestones B (a smaller first test) and A
(the core) also set the release focus (below): the work outside the focus waits; inside it, the priority labels
decide the order.
`python3 tools/release.py` prints the progress of each goal and milestone.

Bug reserve: 0.3

Release focus: A

### Release focus (owner, 2026-11-01)

The next release is a play test: a person plays a full game, and the agents improve what that person sees and does.
Until the next release (a tag `v*`), the agents work only on:

- bugs, and the release checks of the table rows `...-check-...`;
- the features of the milestones that the line "Release focus: X" counts (`A`: the milestones B and A);
- the user experience of the play test: what a player sees, controls and understands in a game (the play-test kit
  `docs/PLAYTEST.md`, the controls, the menus, the hints and the feedback of P9, the start of a game, the speed of
  the server), and the follow-ups of a play test of a person;
- the upkeep of the agent system that the work above needs (tests, CI, the tools of the runs).

All other work waits with the label `after-release`. That includes each feature of milestone C (a feature with no
row), and these kinds of work (the owner moved them first, #4175):

- more input formats and mod content (mod center maps, data mods, script languages such as XS, saved games);
- more ways to make a map (random map scripts from the original files, lobby settings, game modes, export);
- texts in other languages, achievements, statistics and analysis of a game (heat maps, graphs);
- extra replay modes (take over a player), extra commands, a nicer UI of the installer program;
- new systems for the agents (more accounts) and work for later Minecraft versions.

Work that started goes on: a ticket with `in-progress` or an open PR gets no `after-release`. Let it finish and merge,
so that its usage is not lost. Hold only the rest: its epic gets the label and no new sub-issue.

`tools/release.py` prints the features that wait; `framework/tools/usage.py` gives them no refill run. The owner moves
a feature into the focus with its milestone (a row `B` or `A`) or by removal of the label `after-release` from its
ticket. After a release, the owner sets the milestones and the focus of the next release.

## Rules

1. A row names a feature of `steering/project/ROADMAP.md` by its key, or a release check by an id that ends in `-check-...`.
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
| `convert:random-maps` | C | | | |
| `convert:random-maps-more` | C | | | |
| `convert:mood` | C | | | |
| `convert:start-view` | C | | | |
| `convert:terrain-layers` | C | 3 | | |
| `convert:rms-elevation` | C | 3 | | |
| `convert:rms-cliffs` | C | 3 | | |
| `convert:rms-connections` | C | 3 | | |
| `convert:rms-objects` | C | 5 | | |
| `convert:old-formats` | C | 4 | | |
| `convert:rms-players` | C | 4 | | |
| `convert:rms-standard` | C | 6 | | |
| `convert:saved-games` | C | 6 | | |
| `convert:rms-lobby` | C | 4 | | |
| `convert:rms-zr` | C | 4 | | |
| `convert:export` | C | 6 | | |
| `convert:resource-pack` | C | | | |
| `convert:trigger-gaps` | C | | | |
| `convert-check-maps` | B | 5 | A test set of 20 real maps (the ranked map pool, 3 campaigns, 2 old .scx scenarios) converts with no error, no unit in a block and no load error on a server | #2274 |
| `convert-check-look` | B | 3 | A person checks the screenshots of the test set; the fixes of what they find | #2275 |
| `convert-check-speed` | B | 1 | A 480 × 480 map converts in less than 10 minutes and 8 GB | #2276 |

## Play AoE2

| id | milestone | estimate | check | ticket |
|---|---|---|---|---|
| `play:program` | B | | | |
| `play:gather` | B | | | |
| `play:build` | B | | | |
| `play:fight` | B | | | |
| `play:train` | B | | | |
| `play:bot` | B | | | |
| `play:scale` | B | 5 | | |
| `play:menu` | B | | | |
| `play:health` | B | | | |
| `play:military-train` | B | | | |
| `play:tech` | A | | | |
| `play:ages` | A | 6 | | |
| `play:feedback` | B | | | |
| `play:control` | B | | | |
| `play:garrison` | B | | | |
| `play:arrows` | C | | | |
| `play:win` | B | | | |
| `play:walls` | A | | | |
| `play:civs` | C | | | |
| `play:monks` | C | | | |
| `play:market` | C | | | |
| `play:two-players` | C | | | |
| `play:siege` | C | | | |
| `play:naval` | C | | | |
| `play:cheats` | C | | | |
| `play:fog` | C | | | |
| `play:save` | C | | | |
| `play:stances` | C | | | |
| `play:repair` | C | | | |
| `play:diplomacy` | C | | | |
| `play:hunt` | C | | | |
| `play:setup` | C | | | |
| `play:alerts` | C | | | |
| `play:scenario` | C | | | |
| `play:minimap` | C | | | |
| `play:spectate` | C | | | |
| `play:unit-commands` | C | | | |
| `play:speed` | C | | | |
| `play:postgame` | C | 2 | | |
| `play:taunts` | C | | | |
| `play:wildlife` | C | | | |
| `play:farm-reseed` | C | 2 | | |
| `play:game-modes` | C | 4 | | |
| `play:formations` | C | 3 | | |
| `play:town-bell` | C | 2 | | |
| `play:delete` | C | 1 | | |
| `play:auto-gather` | C | 2 | | |
| `play:co-op` | C | 3 | | |
| `play:unit-sounds` | C | 3 | | |
| `play:campaign` | C | 3 | | |
| `play:waypoints` | C | 2 | | |
| `play:auto-queue` | C | 1 | | |
| `play:tech-tree` | C | 2 | | |
| `play:team-chat` | C | 1 | | |
| `play:antiquity` | C | 5 | | |
| `play:auto-scout` | C | 2 | | |
| `play:art-of-war` | C | 4 | | |
| `play:bot-strategy` | C | 6 | | |
| `play:bots` | C | 4 | | |
| `play:attack-ground` | C | 4 | | |
| `play:unique-buildings` | C | 6 | | |
| `play:unique-techs` | C | 105 | | |
| `play:unit-abilities` | C | 6 | | |
| `play:ai-scripts` | C | 8 | | |
| `play:civ-choice` | C | 4 | | |
| `play:ally-commands` | C | 4 | | |
| `play:gaia-units` | C | 3 | | |
| `play:xs-scripts` | C | 10 | | |
| `play:tutorial` | C | 5 | | |
| `play:ratings` | C | 4 | | |
| `play:achievements` | C | 4 | | |
| `play:music` | C | 3 | | |
| `play:languages` | C | 5 | | |
| `play:data-mods` | C | 5 | | |
| `play-check-game` | B | 5 | An agent plays a full game against the bot with a script, from the Dark Age to a win or a loss (about 30 minutes): no server error, no stuck unit | #3324 |
| `play-check-speed` | B | 2 | With 200 units of each player, the server keeps 20 ticks per second | #3325 |
| `play-check-kit` | B | 2 | A play-test kit: how to start and join, the controls, how to report a bug | #3326 |
| `play-check-person` | B | 1 | A person plays one test game | #3327 |

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
| `replay:team-games` | C | | | |
| `replay:minimap` | C | | | |
| `replay:fog` | C | | | |
| `replay:taunts` | C | | | |
| `replay:flares` | C | 1 | | |
| `replay:orders` | C | | | |
| `replay:production` | C | | | |
| `replay:highlights` | C | | | |
| `replay:auto-camera` | C | | | |
| `replay:graphs` | C | 2 | | |
| `replay:army` | C | 2 | | |
| `replay:eco` | C | 2 | | |
| `replay:upgrades` | C | 2 | | |
| `replay:apm` | C | 1 | | |
| `replay:market` | C | 5 | | |
| `replay:relics` | C | 7 | | |
| `replay:build-order` | C | 3 | | |
| `replay:idle-tc` | C | 2 | | |
| `replay:spending` | C | 3 | | |
| `replay:download` | C | 3 | | |
| `replay:restored` | C | 4 | | |
| `replay:live-game` | C | 4 | | |
| `replay:players` | C | 2 | | |
| `replay:pov-camera` | C | 3 | | |
| `replay:game-modes` | C | 4 | | |
| `replay:scenario-triggers` | C | 5 | | |
| `replay:inspect` | C | 4 | | |
| `replay:takeover` | C | 6 | | |
| `replay:heatmap` | C | 3 | | |
| `replay-check-full` | B | 5 | A complex record (a team game of about 40 minutes with castles and large fights) replays from start to end with no error | #2277 |
| `replay-check-follow` | B | 3 | The position tool (#813) shows no stray unit and less than 5 % stuck units on that record | #2278 |
| `replay-check-speed` | B | 2 | The server keeps at least 18 ticks per second at speed 1 through the whole record | #2279 |

## The agent system

| id | milestone | estimate | check | ticket |
|---|---|---|---|---|
| `system:improve` | A | | | |
| `system:reuse` | C | | | |
| `system:structure` | A | | | |
