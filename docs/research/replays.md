# Research: replay a recorded game in Minecraft

Ticket #31. Status: proposal. The owner decides on each milestone before work starts.

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
the `mgz` package has no sample records. The owner must add one record to `samples/` (see the tickets below).

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

## Follow-up tickets (milestone 1)

- #134 Add a short AoE2 DE recorded game to `samples/` (owner, `needs-human`).
- #139 Convert the start state of a recorded game (`.aoe2record`) with `mgz` (depends on #134).

## Sources

- `mgz` on PyPI: https://pypi.org/project/mgz/ (version 1.8.51, MIT license, dependencies).
- `mgz` README, sections "Support" and "Frequently Asked Questions": https://github.com/happyleavesaoc/aoc-mgz
- `mgz` source: `mgz/model/definitions.py` (the `Match`, `Map`, `Tile`, `Object`, `Action` classes) and
  `mgz/fast/actions.py` (the payload of `MOVE`, `ORDER`, `BUILD`, `WALL`).
