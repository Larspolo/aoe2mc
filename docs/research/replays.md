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
records (`aoe.ms`, `data.aoe2companion.com`, `www.aoe2insights.com`) are blocked in the cloud container, and
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
`hd-4.6` is in `samples/`: the other records are larger than 1 MB (`tools/health.py`).

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
