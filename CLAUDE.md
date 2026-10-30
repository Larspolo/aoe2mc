# aoe2mc – guide for Claude Code

aoe2mc converts an Age of Empires II: DE scenario (`.aoe2scenario`) into a Minecraft Java world.
The owner is **Larspolo** (one person, one Claude Max account). The agent works on the project automatically.
The owner steers asynchronously through GitHub Issues (see `framework/docs/STEERING.md`). Each login of `owners` in `agent.toml` steers too; `owner` is the tie-breaker (#4229). The whole agent system (parts, locks, pacing, setup): `framework/docs/SYSTEM.md`.

## Language

Write all text in ASD-STE100 Simplified Technical English: docs, code comments, commit messages,
issue and PR text, status reports. Use short sentences, active voice and the imperative for instructions.
The README already uses this style. Keep it.

## Commands

| Task | Command |
|---|---|
| Install | `python3 -m pip install -r requirements-dev.txt` (a `pip` on the PATH can be another Python) |
| Lint | `ruff check .` |
| Tests of a change (never the full fast suite: the quick CI runs it, #4187; `verify`) | `python3 -m pytest tests/test_a.py ...` (use `python3 -m`: a `pytest` on the PATH can be another Python; `-n auto` for many files, #2415) |
| Slow tests (~2 min) | `python3 -m pytest -m slow` |
| Test scenario | `python3 tools/scenarios.py tiny OUT.aoe2scenario` (or `gallery`, `stress`, `buildings`, `units`, `village`, `facing`, `walls`, `river` (raised river with dock, bridge, boats), `river_town`, `four_civs`, `battle`, `triggers` (timer, area, create and remove triggers; count with `tools/triggers.py FILE...`), `large` (480 × 480 tiles, #690), `owner_loop` (the play-test map of the `human` skill, #1674), `layers` (terrain layers: road, dirt, snow, grass on water, #3690), `moods` (the village with `--mood NIGHT`, a map color mood, #1598)) |
| Convert | `python3 aoe2mc.py IN.aoe2scenario OUTWorld --preview` |
| Look at a world | `python3 tools/world_reader.py OUTWorld [X Y Z]` (`--section x\|z C A0 A1 Y0 Y1`: a vertical section as text) |
| 3D image | `python3 tools/render.py building CASTLE --arch western OUT.png` (`--cut 3`: the rooms inside; or `world OUTWorld X0 Z0 X1 Z1 OUT.png`) |
| Check states | `tools/mcvalid.py` (`block_error`, `entity_error`, `biome_error`, `sound_error`) |
| Coverage of AoE2 types | `python3 tools/coverage.py OUT.md` (designs, mappings, fallbacks). Do not commit `docs/coverage.md`: CI on main does it, and `tools/feature_table.py` for `docs/DESIGN.md` |
| Agent system tools | `health.py`, `operator_check.py`, `feedback.py`, `tokens.py`, `usage.py`, `dashboard.py`, `release.py`: `framework/docs/SYSTEM.md`, "Tools of the system" |
| Server check | `python3 tools/mc_check.py OUTWorld` (headless Minecraft, load errors; `--keep DIR` keeps the saved world), `python3 -m pytest -m mc` |
| Game program | `python3 game/run.py OUTWorld` (Paper server with RCON, `--server vanilla`: Mojang's; type commands; `--bench N`: commands per second; `--play`: gather resources, `--cheats`: the AoE2 cheat codes in the chat; `--replay [--speed N]`: replay a recorded game) |
| In-game screenshot | `python3 tools/mc_shot.py OUTWorld OUT.png [--at X Y Z --look YAW PITCH] [--more X,Y,Z,YAW,PITCH]` (real client, ~25 s per world; `mc_shot.Client`: a player on the Paper server that clicks menus; `--player`: adventure mode, a spectator sees invisible mobs) |

More tools (measurements of time and cost, Minecraft data, random map scripts): `docs/COMMANDS.md`.

Put scratch output (worlds, scenarios, images) in the scratchpad or in `out/` (ignored by git). Never commit worlds.

## Code map

Find code by function name with Grep. Do not read the large files from start to end.

- `aoe2mc.py` – the pipeline, in this order:
  `read_scenario` (parser → terrain arrays, objects, players) → `Columns` (terrain per block column, `ground_detail`)
  → `place_objects` (trees, mines, cliffs, `decor`, calls `buildings.place_building`) → `Edits.by_chunk`
  → `border` (`--border`, blocks outside the map) → `build_chunk` (sections, biomes, block entities) → `write_region` (Anvil `.mca`) and `write_level_dat`.
  Units: `plan_units` → `entity_chunk` (finds free space). `convert()` runs it all; `main()` is the CLI.
- `buildings.py` – `Style` and `ARCH` (9 architecture sets), `CIV_ARCH`, `Canvas` (drawing tools: `room`,
  `timber_room`, `roof`, `gable`, `hip`, `dome`, `cylinder` ...), one function per design, `select()` (name → design),
  `FOOTPRINT`, `place_building()`, `plan_walls()`, `vary()`, `weather()`, `decorate()`, `barriers()`.
- `scx.py` – reader of old scenarios (`.scx` format 1.21): map, players, objects (#311); `aoe2mc.read_scx` converts it (#312).
- `units.py` – `classify()` (AoE2 unit name → entity description), `make_entity()`, `pretty()`.
- `tools/` – test and debug tools (scenarios, world reader, 3D render, Minecraft data, validation).
- `game/` – the game program (#137): `run.Game` starts a Paper server with RCON on the world, `rcon.Rcon` sends commands,
  `plugin/` is the Paper plugin (Java, Gradle wrapper; `run.py` builds it): `aoe moveto`, `aoe attack` with Minecraft path finding (#435),
  `gather.Gather` lets villagers gather wood, food, gold and stone (#138, #391, #390, #392: clicks, sidebar; walks with `aoe moveto` on Paper, #437, own paths on `aoe2mc.json` "ground" only for vanilla),
  `build` places construction sites (#417), `replay.Replay` plays the "timeline" of a recorded game (#374: buildings, chat, ages).
  `ai` gives orders to units with their Minecraft AI through the Paper plugin `game/plugin` (#435, #436: `aoe moveto`, `aoe attack`, `aoe goals`).
  `garrison` sends the selection into an own building and lets it out (#808: `SIZES`, the "inside" cells of `aoe2mc.json`, the menu item "Ungarrison").
- `tests/` – pytest. `conftest.py` has the `tiny_world` fixture (one conversion per session).

## Rules of the domain

Design work (buildings, objects, units, animals) follows `docs/DESIGN.md`. Do design tickets with the `design` skill.

- **Minecraft features first** (owner rule, 2026-10-26; the generic skills say "the platform features first"). Before you write own logic, look for the Minecraft feature that
  does the job, and use it: mob AI and path finding, riders (`Passengers`) and boats, the behavior class of a mob
  (passive, neutral, hostile: `docs/animals.md`), teams, scoreboards, attributes, block states, block entities, redstone,
  datapack functions. Write own logic only when Minecraft has no feature for it, and say why in the PR.
  Converted worlds stay vanilla. The game program may use a Paper plugin where vanilla has no command (for example
  "walk to this point": `Mob#getPathfinder().moveTo`). Details: `docs/DESIGN.md`, section 0.

- Tile (x, y) → block (x × T, z = y × T). T = `--tile-size` (default 4). Elevation level → `--level-height` blocks.
- A building design draws on a `Canvas` in local coordinates. The front (main door) is on the south side (z = w-1).
- Footprint rule: an object keeps its blocks inside its footprint up to head height (3 blocks). `Edits` enforces this.
- Barrier rule: free space in footprints gets `barrier` blocks. Units must never stand in a block:
  the converter prints "units in a block (moved up): N" and N must be 0. Exception: a garrisoned unit stands in the
  barrier blocks of its building, with `Invulnerable` 1 ("units (garrisoned, inside the holder)", #807).
- Block states are strings like `"oak_stairs[facing=north,half=bottom]"`. Each new state must pass `mcvalid`.
- Output is deterministic: all randomness comes from seeded `numpy` generators. Keep it so.
- Target: Minecraft Java 26.3 (`DATA_VERSION = 5023`), the only output (#427). The code uses the 26.3 block and
  entity names and writes the 26.3 entity NBT directly (#428): `mcvalid` checks with 26.3.
  `VERSIONS` in `aoe2mc.py` holds the output profile (`--mc-version`); format changes: `docs/minecraft-versions.md`.
- Global state: `aoe2mc.B` (block registry), `aoe2mc.MOVED`, `aoe2mc.BLOCK_DATA` (extra block entity NBT), `buildings.BARRIERS`, `buildings.TURN` (`--orientation`), `buildings.BRIDGE_CELLS`, `buildings.FLOORS` (gate floors, #773), `buildings.SHELVES` (items of the shelves).
  Tests share `B`, so `B.states` holds the states of all earlier tests.

## Code style

Match the existing code: compact, numpy-vectorized, short comments that say why. Do not reformat code that you do
not change. Do not add a dependency without a ticket that asks for it. Keep functions in their present file.
Game data (AoE2 units, buildings, technologies, objects, terrains, civilizations, their values) goes in a `.jsonl` data
file, not in a literal of the code: the fast test of `tools/data_lint.py` fails on a new one (#1909). Where a table is
still in the code, add each entry on its own line, in alphabetical order, not at the end (#655, #670).
**Before you add a new item, key, setting, mode, plugin command or trigger type, or a test of a data file, read
`docs/extend.md`**: it names the one line that each one needs, so that parallel tickets do not conflict.
**No test checks the content of a data file or a configuration file** (owner, 2026-10-29): a change of a value, a text
or a setting there must not make a test fail. Test the form of the data and the behavior of the code, with the
expected value computed from the data or with test data (a fixture, a temporary file).
A change of data files only adds no test, also when the ticket asks for one (#4242; `framework/tools/ship_pr.py` stops it).

## How to verify

There is no Minecraft window here. Use, from cheap to expensive: lint and fast tests → slow tests → convert a
scenario with `--preview` and look at the PNG with the Read tool → `tools/world_reader.py` for exact blocks
→ `tools/mc_check.py` for load errors in a real Minecraft server → `tools/mc_shot.py` for in-game screenshots
(before a `needs-human` ticket).
Details: the `verify` skill.

@framework/CLAUDE.md

@docs/LEARNINGS.md
