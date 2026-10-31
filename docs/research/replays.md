# Research: replay a recorded game in Minecraft

Ticket #31. Status: the owner decided on 2026-10-25: full support (epic #371); milestones 2 and 3 are tickets
(see "Follow-up tickets (full replay)").

## Summary

A recorded game (`.aoe2record`) does not store where the units are at each moment. It stores the start state
and the commands of the players. Only the game engine can turn the commands into positions. Thus an exact
replay is not possible without a full AoE2 simulation, and that is too large for this project.

Some parts are exact and cheap: the map and the start units (the header), and the time and place of each
building that a player ordered (the `BUILD` and `WALL` commands). The proposal starts with these.

## What a record contains

| Part | Content | Exact? |
|---|---|---|
| Header | A snapshot of the start state: map size, terrain and elevation of each tile, all objects (gaia and players) with their type ID and position, players (name, civilization, color, team), game settings | yes |
| Body | The commands of the players with a time stamp: `MOVE`, `ORDER`, `BUILD` (building type, tile, builders), `WALL` (start and end tile), `MAKE`/`QUEUE` (train units), `RESEARCH`, `DELETE`, `GATE`, `RESIGN` and more | yes, as commands |
| Body | View locks (where each player looks), chat, age-up times | yes |
| Not in the file | Unit positions after the start, hit points, deaths, resources, the result of a fight, the finish time of a building | no |

The `mgz` FAQ says it clearly: the header "is a snapshot of the initial game state", the body "is a list of
moves made by players", and the number of resources or kills at a time is not known "without replaying the
match in-game".

The type IDs in the header are the same unit and building IDs that `read_scenario` uses (`UnitInfo`,
`BuildingInfo`, `OtherInfo` of AoE2ScenarioParser). The terrain IDs are the same too. Positions are tile
coordinates (floats). The `mgz` model does not give the rotation of objects: use 0.

## Parsers

| Parser | Language | License | AoE2 DE support | Notes |
|---|---|---|---|---|
| `mgz` (happyleavesaoc/aoc-mgz) | Python ≥ 3.7 | MIT | header and commands up to the newest DE version. The `full` body parser stops at DE 26.21; the `fast` body parser and the `model` work on newer files | 1.8.51 on PyPI (2026-02-01). Dependencies: `aocref` (object names), `construct==2.8.16` (exact pin), `tabulate`. No conflict with the present requirements |
| `genie-rec` (SiegeEngineers/genie-rs) | Rust | not checked | not checked | Listed as a resource in the `mgz` README |
| `recage` (goto-bus-stop/recage) | JavaScript | not checked | not checked | Listed as a resource in the `mgz` README |
| `aoc-mgx-format` (stefan-kolb) | documentation | — | old versions only | Format description |

Recommendation: use `mgz`. It is Python, MIT, maintained, and its `model.parse_match()` gives the data that
the converter needs (`match.map.tiles`, `match.gaia`, `match.players[i].objects`, `match.actions`,
`match.inputs`, `match.uptimes`, `match.chat`).

Tested here: `pip install mgz` in a venv works with Python 3.11. No record was parsed: the hosts that serve
records (`aoe.ms`, `data.aoe2companion.com`, `www.aoe2insights.com`) were blocked in the cloud container. Update (2026-10-29): `aoe.ms` works now (`docs/ENVIRONMENT.md`), but `mgz`
1.8.51 cannot read a record of 2026-10-28 (`RuntimeError: could not parse` in `mgz/fast/header.py`), and
the `mgz` package has no sample records. Update (#134): `samples/de-64.3.aoe2record` is a DE test record of the
`mgz` repository (MIT, GitHub raw). `mgz.model.parse_match` reads it.

### Object IDs (#407)

The commands name objects by ID (`"objects"`, `"target"` in `read_timeline`). The rules, from
`samples/de-64.3.aoe2record`:

- Start objects keep the ID of the record (`instance_id`, `ref` in `read_record`). GAIA animals that a player
  takes keep their ID too: player 2 moves the GAIA goats 8380–8383 at 25 s.
- The game gives each new object the next free ID, in the order that it makes the objects. The first new ID is
  the highest start ID + 1 (the start flares are 9912 and 9913). A foundation gets its ID at the BUILD command (one
  per wall tile), a unit when its training ends. Example: the houses at 3.1, 3.5, 4.6 and 5.4 s fit 9914–9917 (no
  command selects them). The
  first villagers end their training at 25.9 s (player 2, 9918) and 27.0 s (player 1, 9919). The lumber camp of
  player 1 (BUILD at 123.2 s) is 9933, and the villager of player 1 that ends at 127.0 s is 9934.
- Objects that the record does not show take IDs too (9920, 9921, 9924 and 9927–9930 in the first 100 s; later
  also arrows and dead units). So a counter alone loses the count.
- The `player` of a command is not always correct: some MOVE commands show for both players (6.8 s, the goat
  1557 of player 1). Use the objects, not the player.

`aoe2mc.name_timeline` uses these rules. It predicts the new objects (BUILD and WALL foundations, QUEUE units at
the end of the queue of their building: `TRAIN`, `RESEARCH_S`) and matches each one to the first ID in the next 16
IDs that the commands use in the same way: a building ID in QUEUE and RESEARCH (and of the building that trains
its units), a unit ID in MOVE, ORDER and BUILD, not used before the object exists. An ID that a command uses before
the command of the new object is older. A building that is not matched gets the name of its units' building. It
adds `"names"` to the events. Result on the samples (the IDs that player 1 selects in MOVE, ORDER and BUILD):

| Record | First 5 minutes | Whole game |
|---|---|---|
| DE 64.3 (`samples/`) | 33 of 33 | 113 of 247 |
| DE 63.0 | 19 of 20 | 63 of 72 |
| DE 61.5 | 27 of 35 | 114 of 202 |
| DE 25.01 | 31 of 34 | 187 of 409 |

Later in a game, fights make many objects that the record does not show (arrows, dead units), and the queues of
the record do not show cancelled units, so the match finds fewer IDs.

### Game versions (#376)

The test records of the `mgz` repository (`tests/recs/`, MIT), read with `mgz` 1.8.51. "Model":
`mgz.model.parse_match` (map, objects and commands). "Header": `mgz.summary.full.FullSummary` (map, players,
start objects; no commands). The converter uses the model, and the header for the games that the model cannot
read (`aoe2mc.read_old_record`). The header parser skips the GAIA trees of these versions: `read_old_record`
turns the skip off (about 1 s more).

| Record | Version | Model | Header | Converter |
|---|---|---|---|---|
| `up-1.4.mgz` | UserPatch 1.4 | no ("not supported") | yes | start state, 1812 objects |
| `small.mgz` | UserPatch 1.5 | no | yes | start state, 2046 objects (object 917 unknown ×8) |
| `hd-4.6.aoe2record` | HD 4.6 | no | yes | start state, 2765 objects (`samples/`, test) |
| `hd-5.5.aoe2record` | HD 5.5 | no | yes | start state, 20323 objects |
| `hd-5.8.aoe2record` | HD 5.8 | no | yes | start state, 9521 objects |
| `de-12.97-6byte-tile.aoe2record` | DE 12.97 | no | yes | start state, 1881 objects |
| `de-13.07.aoe2record` | DE 13.07 | no | yes | start state, 2695 objects |
| `de-13.34.aoe2record` | DE 13.34 | yes | yes | start state and timeline |
| `de-25.01.aoe2record` | DE 25.01 | yes | yes | start state and timeline |
| `de-50.6-scenario.aoe2record`, `-with-triggers` | DE 50.6 (scenario game) | no | no | error message |
| `de-61.5.aoe2record` | DE 61.5 | yes | yes | start state and timeline (object 649 unknown ×444) |
| `de-62.0.aoe2record` | DE 62.0 | yes | yes | start state and timeline (object 649 unknown ×430) |
| `de-63.0.aoe2record` | DE 63.0 | yes | yes | start state and timeline |
| `de-64.3.aoe2record` | DE 64.3 | yes | yes | start state and timeline (`samples/`, tests) |

The converter reads `.aoe2record`, `.mgz` (UserPatch), `.mgx` (AoC) and `.mgl` (AoK). `--at` needs the
timeline: for a game without one it stops with "mgz cannot read the commands of this recorded game". Only
`hd-4.6` is in `samples/`: the other records are larger than 1 MB (`framework/tools/health.py`).

### Team games (#1190)

The records of the table that `mgz.model.parse_match` reads, by players (`mgz` 1.8.51, `aoe2mc.read_timeline`):

| Record | Players | Teams | Map | Length | Size |
|---|---|---|---|---|---|
| `de-13.34.aoe2record` | 2 | 1 vs 1 | Arabia | 44:42 | 4.5 MB |
| `de-25.01.aoe2record` | 2 | 1 vs 1 | Arabia | 44:01 | 3.0 MB |
| `de-61.5.aoe2record` | 2 | 1 vs 1 | Arabia | 27:54 | 3.8 MB |
| `de-62.0.aoe2record` | 2 | 1 vs 1 | Arabia | 18:07 | 2.2 MB |
| `de-63.0.aoe2record` | 4 | 2 vs 2 (players 1 + 3, 2 + 4) | Arena (Medium, 168 tiles) | 23:28 | 3.0 MB |
| `de-64.3.aoe2record` | 2 | 1 vs 1 | Acropolis | 44:22 | 5.7 MB |

Result: `de-63.0` is the team game for the tests (`samples/`, MIT, `tests/test_record_team.py`). Its timeline has
2347 commands of all 4 players (build commands of each player) and ends with a resign of player 4. The converter
makes 672 × 672 blocks in 15 s, with 84 units and 0 units in a block. No test record has 8 players.

## Options for the replay in Minecraft

| Option | What the player sees | Accuracy | Cost |
|---|---|---|---|
| A. Start state | The map and the start units of a record, like a converted scenario | exact | S–M: a second reader next to `read_scenario` |
| B. Build timeline (datapack) | Buildings and walls appear at the time of the player's command, at the right place. A datapack with `/schedule` functions places each building (`/place template` with one structure file per building, or `/fill` and `/setblock`) | place and order exact; the time is the command time, not the finish time; buildings that are cancelled or destroyed stay | M–L |
| C. Snapshots at fixed times | One world per time step (for example each 5 minutes) with the buildings of option B | as option B, no runtime code | M (reuses the converter, one conversion per step) |
| D. Approximate units | Units walk in straight lines to the target of each `MOVE`/`ORDER` command (`/tp` steps in a datapack, or display entities) | low: no paths, fights, deaths or gathering; new units need the object ID rules of the game | L |
| E. Full simulation | An exact replay | exact | not feasible: it needs a reimplementation of the AoE2 engine. The open-source engine project `openage` is not complete and is GPL |

A server mod (Fabric or Paper) can do options B and D with more control than a datapack. It needs Java code and
a build for each Minecraft version. A datapack works on vanilla servers and in single player, and the converter
can write it into the world folder. Prefer the datapack.

## Proposal: milestones

1. **Convert the start of a recorded game** (option A). `aoe2mc.py IN.aoe2record OUTWorld` reads the header
   with `mgz` and converts the map and the start units like a scenario. Useful alone: every played game becomes
   a map. Size: one M ticket, after a sample record exists.
2. **Build timeline** (option B or C). The owner chooses the datapack or the snapshots. Research the
   datapack format of the target version first (`docs/minecraft-versions.md`).
3. **Approximate units** (option D). Only if the owner wants it after milestone 2. Low accuracy.

Not planned: option E.

## State of the replay

Usage: README, section "Use". Two outputs use the timeline of a record (`aoe2mc.read_timeline`, #372):
- `aoe2mc REC W --at MM:SS` (#373): a world at that time. Buildings and walls of the build commands stand, trained
  units stand at their building.
- `game/run.py W --replay [--speed N] [--from MM:SS]` (#374): plays the timeline on a server. Buildings appear at
  their command time, chat is `/tellraw` in the player color, age-ups and resigns are a title, research is an action
  bar line (#374). Trained units appear in front of their building when the training ends (#408, IDs: #407). Units
  of `MOVE` and `ORDER` walk on a path to the target at their AoE2 speed (#409), a group stops in a line formation
  (#410). Old game versions: #376.

Control of a live replay (decision of the owner in #686: hotbar items, a chest for more actions, and a command
for each action; #688, `game/replay_input.py`): a right click with the clock pauses and continues, the feather sets
the next speed (0.5, 1, 2, 4, 8×), the ender pearl jumps 1 minute forward, and the chest in the last slot opens a chest
menu with all actions (Paper only). `/trigger aoe_replay set N` does action N (1 pause, 2 next speed, 3, 5, 6 jump 1, 5,
10 minutes, 8, 9 back 1, 5 minutes, 10-14 speed 0.5-8×); a clickable chat line lists them. The items are carrots on
a stick with an `item_model`: Minecraft counts their right clicks (`minecraft.used`), not those of a clock.
A jump back (#979): the replay keeps no earlier states, so `game/run.py` saves the world at the start, and for a jump
back to T it stops the server, puts the saved world back (the player files stay), starts the server on the same port
and plays a fresh replay that jumps forward to T (`replay.live`). The players join again (about 10 to 20 s).

Not possible from the record alone: fights and deaths, gathering, destroyed or unfinished buildings, cut trees,
used mines and farms, and the exact unit paths. Next: #438 lets Minecraft path finding walk the units (epic #433).

## Follow-up tickets (milestone 1)

- #134 Add a short AoE2 DE recorded game to `samples/` (owner, `needs-human`).
- #139 Convert the start state of a recorded game (`.aoe2record`) with `mgz` (depends on #134). Done: `aoe2mc.read_record`.

## Follow-up tickets (full replay)

- #372 Read the commands into a timeline. Done: `aoe2mc.read_timeline`, the key `timeline` of `aoe2mc.json`.
  mgz 1.8.51 gives `ERROR` for each `DE_QUEUE` (train units) of a DE 64.3 record: `aoe2mc.de_queue` reads them.
  Each `WALL` command of the sample is one tile (start = end).
- Milestone 2 (build timeline): #373 Convert a recorded game at a chosen time (`--at MM:SS`),
  #374 Replay a recorded game live in the game program.
- Milestone 3 (approximate units): #375 Move the units of a recorded game in the live replay.
- #376 Read recorded games of other game versions.

## Sources

- `mgz` on PyPI: https://pypi.org/project/mgz/ (version 1.8.51, MIT license, dependencies).
- `mgz` README, sections "Support" and "Frequently Asked Questions": https://github.com/happyleavesaoc/aoc-mgz
- `mgz` source: `mgz/model/definitions.py` (the `Match`, `Map`, `Tile`, `Object`, `Action` classes) and
  `mgz/fast/actions.py` (the payload of `MOVE`, `ORDER`, `BUILD`, `WALL`).

## Taunt sounds (decision #2233, 2026-10-28)

A taunt plays a vanilla Minecraft sound only when a good Minecraft sound fits it ("Yes", "No", a laugh); all other
taunts show only their text. The AoE2 taunt sounds are not free to copy (#2662).

## Live graphs (decision #3447, 2026-10-29)

The live replay shows the graphs of each player (population, villagers, military, estimated resources, epic #3445)
as a large text display "chart" in the sky above the overview view: one row per player in its color, one bar
character (▁▂▃▄▅▆▇█) per game minute. It is vanilla (P2, P3). The owner checks the graphs in the game; a map item
with a real line graph (Paper `MapRenderer`) can replace it later (P4).
Owner decision of #3924 (2026-10-29): no text in the sky at the center. The graphs, the army and build order, the
upgrades and the economy are written books in the hotbar slots 3 to 6 (`replay.STAT_BOOKS`). The book font has only
the bar characters ░▒▓▄█, so a bar is a shade (░▒▓█).

## Save version 68.9 (#3686, 2026-10-29)

mgz 1.8.51 and its GitHub HEAD read DE records up to save version 66.6. A ranked 1v1 game of 2026-10-27 (save 68.9,
from `api.ageofempires.com`, not committed: no license) has two changes in the DE header (`mgz.fast.header.parse_de`),
found by a comparison of the bytes with `samples/de-64.3.aoe2record`:

| Place | 64.3 and 66.6 | 68.9 |
|---|---|---|
| End of each player, after the 4 bytes of 64.3 | next player | one more DE string (`60 0a 00 00`: empty in the test record) |
| After the DE string before the 8 bytes and the timestamp | 8 bytes, timestamp | two more DE strings (empty), then 8 bytes, timestamp |

The metadata, map, players and actions read as for 66.6. The scenario and the lobby do not: mgz reads the lobby of a
68.9 record from a wrong place with no error (all zeros); `lobby_at_end` fixes it (#5178, `docs/research/saved-games.md`). `aoe2mc.new_saves()` adds the
three reads to the source of `parse_de` (for save > 66.6). With it `read_record` and `read_timeline` read the test
record: map Arabia (120 tiles), 2 players with names and civilizations, 1325 timeline events.

Patch for upstream mgz (`mgz/fast/header.py`, `parse_de`; a ticket of the owner, as an upstream issue is public):

```diff
         if save >= 64.3:
             data.read(4)
+        if save > 66.6:
+            de_string(data)
 
         players.append(dict(
@@
     if not skip:
         de_string(data)
+        if save > 66.6:
+            de_string(data)
+            de_string(data)
         data.read(8)
```

### A scenario game of save 68.9 (#5203)

`samples/de-trigger-test.aoe2record` (the scenario `trigger_test`) stops in `mgz.fast.header.parse_scenario`, not
in the DE header. The scenario file name (`aoc_string`) is not at the place of 66.6: it is 128 bytes later, after the
64 bytes of DE. In a random map game both places hold an empty string, so the old read worked by chance. For save
> 66.6, `new_saves()` reads 62 bytes after the 64, then the file name, then 4 bytes (not 68), then the 20 bytes as
before. Two more steps of `mgz.model` fail for a scenario game: the instructions name no map (`could not detect
encoding`; DE is UTF-8) and the map id 4294967293 is no builtin map. `new_saves()` makes both a custom map.

## Pitfalls

Moved from `docs/LEARNINGS.md` (improve run, 2026-10-26).

- Test data: `samples/de-64.3.aoe2record` (`mgz`, MIT, #134; each town center 4 times, #139). `parse_match(f).actions`:
  `ERROR` actions are commands mgz could not read (all `DE_QUEUE` in DE 64.3: `aoe2mc.de_queue`; raw bytes: a wrapper
  of `mgz.fast.parse_action`, #372). Old `.scx` (no license, do not commit): GitHub raw
  `SiegeEngineers/genie-rs/master/crates/genie-scx/test/scenarios/` (format 1.21: `Age of Heroes b1-3-5.scx`).
- `mgz.model.parse_match` reads only DE 13.34 and later; `mgz.summary.full.FullSummary` reads HD, UserPatch and older DE
  but skips the GAIA trees (`aoe2mc.read_old_record` turns the skip off). More test records: GitHub raw
  `happyleavesaoc/aoc-mgz/master/tests/recs/` (table in `docs/research/replays.md`, #376). `construct` 2.8: `IfThenElse` is a `Switch`.
- Record commands: the `player` of an mgz action is not always right (a MOVE shows for both players), and the
  `objects` of SPECIAL are not IDs. New objects take the next free ID: `aoe2mc.name_timeline` (#407).
- mgz `Inputs.add_action` fills a command without object IDs with the last IDs of its action type of any player: player 2 "moved" the villagers of player 1 (#828). `read_timeline` parses in `aoe2mc.own_selection()` (the last IDs of the same player). The selection of a player is its own: check the owners of the IDs (`tests/test_record_selection.py`).
- Garrisons (#809): DE has no own garrison action in `mgz`. The garrison button and a right click with the garrison cursor are SPECIAL with `order` "Garrison" (order 5) and the building in `target`; `mgz.fast` reads their `objects` one byte early (ID × 256). `read_timeline` gives them as kind `garrison` with the real IDs. UNGARRISON has the building IDs in `objects`. `samples/de-64.3.aoe2record`: 20 garrison commands (11 on a start town center), 8 ungarrisons (5 of a start town center), 3 ORDERs on an own start town center.
- A broken state of `replay.Replay` (for example a unit in `moving` with an empty path, #1177): wrap each function of `vars(replay.Replay)` (only plain functions: a wrapped staticmethod breaks) with a check of the state before and after, and play the jump with the fake clock of `tests/test_replay_control.py`. The wrapper names the method that breaks it (`enter`) in one run (about 2 minutes for 43:30 of `samples/de-64.3.aoe2record`).
- A summary or an estimate that is too low after a jump: look first for record commands that the replay ignores (`back_to_work` left 18 villagers in a town center, #1179). Count the `kind` values of the timeline against the cases of `Replay.commands`.
- Low resources of one player (#1229): sum the villager seconds by the kind of the last command of each villager (`order:<target name>`, `build:<name>`, `move`) up to the time. Commands that gave nothing were hunts (`SHEEP`, `WILD_BOAR`, `IBEX`), camp builds and units that stayed inside a building after an ORDER on it. An ORDER selection can hold sheep next to the villagers: only villagers gather.
- The stuck units of a `tools/replay_drift.py --log` file: use `replay_drift.analyze()` or its rule (distance less `slack`, grouped by `uuid`). The raw distance of a walking unit includes the rest of its leg: #1291 first named two units that were on time (30–45 blocks raw, 0 less the slack). The result also changes from run to run (2 or 3 stuck villagers on the same commit): run it twice before you call a unit fixed.
- `tools/replay_drift.py` imports `replay` only after the conversion and the server start: do not stash or check out files during a run, else it can measure the old code (#1293).
- `Replay.units` holds the start units of aoe2mc.json only after the first `grid()` call (a move, a build ...): a pass over all units (`fog`, #1302) calls `self.grid()` first, else a replay with only chat events has no units. `Replay.view` is the camera place of `overview()`, not a player.
- A replay ticket that moves one unit: reproduce it offline first (a `Replay(Fake(), data)` over the timeline of the converted record, the unit put in by hand: the units of a record exist only on a server), not with three `replay_drift.py` runs of 10 minutes (#1275).
- A stuck unit of a live replay: an `x` or `z` of exactly N + 0.3 (half the width of a villager) means a block face stops it. Read the blocks with `execute if block X Y Z minecraft:air` on the live server (a `save-all` copy can miss chunks), and the entity with a path (`data get entity U Pos`, `Brain.memories."minecraft:walk_target"`): the full `data get entity U` is cut with "..." (#2304: a moss carpet step under leaves 2 blocks up).
- `Replay.run` sends commands only at an event or a step candidate (the `step = min(...)` list: walks, gather steps, texts, builds, flare bursts). A repeated effect that lives longer than one command (a particle column) needs its own candidate, else it shows only when a unit walks (#2506). A check with a real client: count the commands per second in a wrapped `game.command`; a minimap mark that blinks (`PERIOD` 20 ticks) needs shots over 2 s.
- A level-4 check of a live replay effect (#2410): run `run.replay(game, world, 1.0, "6:55")` in a daemon thread next to `mc_shot.Client`, and wrap a `Replay` method (`flare`, `expire`) to log the wall time of its commands: the shots then follow the event, not a guessed jump time. `Game.folder` is a temporary folder: copy `logs/latest.log` before the `with` ends. The replay takes the player out of spectator mode: hold the map in the offhand for the minimap.
- `tools/replay_drift.py` numbers change from run to run of the same code (#2633, de-64.3 to 38:00: "stuck" 11 and 27, villagers "died" 2 and 25 when an eagle scout chose other targets): compare the long cases of named units (`ref`, seconds far) with a script over the `--log` file, not the table totals, and run the after case twice.
- A level-4 check of a replay order (patrol, move) compares the unit with its replay place (`Replay.at(v, t)`, the `aoe moveto` goals of an offline `Replay(Fake(), data, ai=True)` run), not with the place of the entity: after a jump (`run(to=...)`) a scout was 50 blocks behind its replay place, and #2630 was a wrong bug ticket (#2564). Map a record ID to its replay unit: `r.units[ID].name` (the names of `aoe2mc.name_timeline`).
- A timing measure of the live replay (`tools/replay_drift.py`, the `"slack": 0` samples of a loop that is behind its clock) needs the CPU alone: a `pytest -n 3` in the same minutes slowed the replay loop of de-63.0 to about speed 2, and the run had to start again (#2761). Run the before and after cases in one background script, one after the other, and do no tests during it.
- On Paper `Replay.run` sends its commands in `aoe batch` commands (#2960, `run.batches`): a server test that wraps `game.command` to see one command (a `tellraw` time, a `bossbar` answer) must decode the batch (`urllib.parse.unquote_plus` of each word after `aoe batch`) or set `game.batch` to send one by one. The time of the replay loop on a large map is the server tick: after 16:00 of de-63.0 the mean tick is 40 to 50 ms and each RCON round trip waits 2 to 5 ms (#2761).
- `tools/replay_drift.py` numbers depend on the CPU load and change much from run to run: a `pytest -n 2` run next to it made the mobs late, and two runs of the same code gave 9 and 12 stuck villagers on de-63.0 (#2634). Run the before and after measurements alone, one after the other. After about 20 minutes of de-63.0 at speed 4 the replay loop is behind its clock (walking samples with `"slack": 0`, #2761): the later rows measure the lag, not the units. Before a fix of a drift ticket, `git log origin/main -- game/replay.py`: the drift tickets of one check (#2278) ran in parallel, and #2652, #2724 and #2733 fixed most of #2634 first.
- Stuck units with an order in groups (`order` true, 30 to 80 blocks behind for 30 s and more) can come from the Python loop of `Replay.run`, not from the mobs: a slow `commands(e)` holds all orders, and the samples of `tools/replay_drift.py` use the clock. Wrap `Replay.commands` with `time.monotonic` and `cProfile` in a script that calls `replay_drift.main` (#2881, #2953: 12 path searches to an enclosed goal, 8 s of real time).
- `Replay` already has the method `entity(v)` (the live position of a unit, about 10 callers): a new method with that name replaces it with no error until a test calls it ("takes 2 positional arguments but 4 were given", #3028). `grep -n "    def NAME" game/replay.py` before you add a method. A setup of `run.play` (a scout swap, the start buildings, the town of a mode) writes "summon", "delete" and "build" events with `"free": true` at 0:00 (`record.summoned`, `record.removed`, #3028): only while `Recorder.setup` is true, until `record.play()`.
- A live replay that falls behind its clock with a server tick (`/tick query`) above 50 ms is slow in the server, not in RCON: profile the server thread with the JDK (`jcmd PID JFR.start settings=profile`, later `jcmd PID JFR.dump name=1 filename=F.jfr`, `jfr print --events jdk.ExecutionSample F.jfr`, the frames of "Server thread"). #2761: 65 % was the vanilla villager brain (`YieldJobSite.canReachPos`, the path searches of villagers with no profession near a job site), fixed with nitwits (`units.IDLE_JOB`).
- A drift cause in the path searches of the live replay: replay the whole converted record offline first (`Replay(Fake(), data, ai=True).run(speed=1000, clock=..., sleep=...)`, 25 to 80 s, no server) with `gather.Map.path` wrapped: count the failed searches (blocked start, at the limit, fast) and the search seconds per game minute, before and after the change. In #2881 it found the cause (a new order searched from a cell in a lake) in minutes, and a regression (153 searches of 0.2 s in one game minute by `chase()`) that a drift run shows only as stuck units.
- A unit of a live replay that fights another entity than its order target: first check that the replay sent `aoe attack` at all (`far()` turns an ORDER into a walk to its tile, and the sight then takes the nearest enemy). To see each target change, log `setTarget` of `AoePlugin.java` with the caller line (`new Throwable().getStackTrace()`), run `tools/replay_drift.py --server-log` and match the UUIDs of the `--log` file (#3636). A record has no tag `aoe2mc.r<ref>`.
- `Replay.census()` runs only with `Replay(..., ai=True)` and `run(..., bar=True)` (as `run.py --replay`): a test of the losses (`fallen`, `lost`) with a fake census needs both, else it never asks the fake (#3843). In `de-64.3` the first archers of player 2 come after 15:00.
- `Replay.jump()` has its own event loop: an event kind that `commands()` handles for the state (estimate, rates, ages) must also go into `jump()`, else a `--from` start loses it (#4162: trades and tributes).
- A count of the commands of a record by plain `mgz` misses the DE_QUEUE commands (ERROR, 2 in the first 5 minutes of `de-64.3`): patch the reader as `read_timeline` does (`de_queue`, `new_saves`, `own_selection`, #3842).
- The offline replay (`Replay(Fake(), ...)`) has no fights: a villager that dies in the game stays in `units` and counts as idle to the end. In `de-64.3` 60 to 70 % of the offline idle time goes to villagers with no later record command, and player 1 has 221 units at 44:00 (cap 200). Measure the idle time of the live summary on Paper (`tools/replay_drift.py`, the census buries the dead, #3885, #4063).
- `aoe2mc.name_timeline` writes the names into the events of the timeline: a measure script that calls it before `Replay(...)` changes the replay (#4063: P1 idle time 204 → 152 min). Since #4063 the summary counts the idle time of a villager only up to its next record command (`Replay.told`).
- The `data()` fixture of `tests/test_replay.py` gives player 2 the architecture `meso`, which `buildings.ARCH` does not have: a BUILD event of player 2 in a replay test raises `KeyError: 'meso'`. Build for player 1 (#4662).
- `Replay.play` sends the end commands (the "Replay ended" title, the summary, the books) only with `bar=True`, as `run.replay` calls it: a test of the end of a replay with the default `bar=False` sees none of them (#4664).
- No record of a game mode (Regicide, King of the Hill ...) is in `samples/`: #4834 found none (the record API lists no lobby games, and `mgz` 1.8.51 cannot parse current records). A test of a mode replay uses a fake replay with a `lobby` of test data (`tests/test_replay_regicide.py`, #4835); `mgz` gives the type names (`mgz.reference.get_consts()["game_types"]`).
- The world of a record with `--scenario FILE` does not start its timer triggers (#5158): the replay clock runs them from aoe2mc.json "timers" (`aoe2mc.timer_list`, `Replay.trigger`). A test of a trigger in a replay puts that list into its `data()`; the triggers that "(De)Activate Trigger" names stay on the server schedule (`aoe2mc.replayed`).
- A header part that mgz parses with no error can still come from a wrong place: mgz read the lobby of a save 68.9 record as all zeros (#5178). Check the values (population 200, the team lock), not only that the parse ends.
