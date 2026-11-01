# aoe2mc – guide for Claude Code

aoe2mc converts an Age of Empires II: DE scenario (`.aoe2scenario`) into a Minecraft Java world.
The owners (`owners` in `agent.toml`; `owner`, Larspolo, decides, #4229) steer through GitHub Issues (`framework/docs/STEERING.md`).
The agent system: `framework/docs/SYSTEM.md`. Write all text in ASD-STE100 Simplified Technical English (short sentences,
active voice, imperative), as the README does.

## Commands

Use `python3 -m` (another Python can be on the PATH). Rare tools and options: `docs/COMMANDS.md`.

| Task | Command |
|---|---|
| Lint | `ruff check .` (`--fix` sorts the imports, rule `I`, #4557) |
| Tests of a change | `python3 -m pytest tests/test_a.py ...` (`-n auto` for many files). Never the full fast suite: the quick CI runs it (#4187). Slow: `-m slow`; server: `-m mc` |
| Test scenario | `python3 tools/scenarios.py tiny OUT.aoe2scenario` (more names: `docs/COMMANDS.md`) |
| Convert | `python3 aoe2mc.py IN.aoe2scenario OUTWorld --preview` |
| Look at a world | `python3 tools/world_reader.py OUTWorld [X Y Z]` (`--section x\|z C A0 A1 Y0 Y1`) |
| 3D image | `python3 tools/render.py building CASTLE --arch western OUT.png` (`--cut 3`; `world OUTWorld X0 Z0 X1 Z1 OUT.png`) |
| Check states | `tools/mcvalid.py` (`block_error`, `entity_error`, `biome_error`, `sound_error`) |
| Server check | `python3 tools/mc_check.py OUTWorld` (headless Minecraft, load errors; `--keep DIR`) |
| Game program | `python3 game/run.py OUTWorld` (Paper server with RCON) |
| In-game screenshot | `python3 tools/mc_shot.py OUTWorld OUT.png` (real client, ~25 s) |

Put scratch output in the scratchpad or in `out/`. Never commit worlds.

## Code map

Find code by function name with Grep. Do not read the large files from start to end.

- `aoe2mc.py` – the pipeline: `read_scenario` → `Columns` → `place_objects` (calls `buildings.place_building`)
  → `Edits.by_chunk` → `border` → `build_chunk` → `write_region` and `write_level_dat`. Units: `plan_units` →
  `entity_chunk`. `convert()` runs it all; `main()` is the CLI. `scx.py` + `read_scx`: old `.scx` scenarios.
- `buildings.py` – `Style`, `ARCH`, `CIV_ARCH`, `Canvas` (drawing tools), one function per design, `select()`,
  `FOOTPRINT`, `place_building()`, `plan_walls()`. `units.py` – `classify()`, `make_entity()`.
- `game/` – the game program: `run.Game` (Paper server, RCON), `gather.Gather`, `build`, `replay.Replay`, `ai`,
  `garrison`; `plugin/` is the Paper plugin (Java; `aoe moveto`, `aoe attack`, `aoe goals`).
- `tools/` – test, debug and agent tools. `tests/` – pytest; `conftest.py` has the `tiny_world` fixture.

## Rules of the domain

Design work follows `docs/DESIGN.md` and the `design` skill.

- **Minecraft features first** (owner rule): before own logic, use the Minecraft feature that does the job (mob AI,
  path finding, riders, teams, scoreboards, attributes, block states and entities, datapack functions). Write own
  logic only when Minecraft has none, and say why in the PR. Worlds stay vanilla; the game program may use the Paper
  plugin where vanilla has no command. Details: `docs/DESIGN.md`, section 0.
- **Release focus** (owner): until the next release, work only on bugs, release checks, the release milestone
  (the scope of the release epic, label `release`), the features in the focus and the user experience of the play test. Give other work
  `after-release`. The epic's close makes the release (`steering/project/RELEASE.md`, "Release cycle").
- Tile (x, y) → block (x × T, z = y × T), T = `--tile-size` (4). A design draws on a `Canvas` in local coordinates,
  the front (main door) on the south side (z = w-1).
- An object keeps its blocks inside its footprint up to head height (3 blocks, `Edits`). Free footprint space gets
  `barrier` blocks. "units in a block (moved up): N" must print 0 (garrisoned units excepted, #807).
- Block states are strings like `"oak_stairs[facing=north,half=bottom]"`; each new one must pass `mcvalid`.
- Output is deterministic: all randomness comes from seeded `numpy` generators.
- Target: Minecraft Java 26.3 (`DATA_VERSION = 5023`) only, with its block and entity names and NBT (`VERSIONS`,
  `docs/minecraft-versions.md`).
- Global state: `aoe2mc.B` (block registry; tests share it), `aoe2mc.MOVED`, `aoe2mc.BLOCK_DATA`, `buildings.BARRIERS`,
  `TURN`, `BRIDGE_CELLS`, `FLOORS`, `SHELVES`.

## Code style

Match the existing code: compact, numpy-vectorized, short comments that say why. Do not reformat other code, add a
dependency without a ticket, or move functions to another file. Game data goes in a `.jsonl` data file, not in a code
literal (`tools/data_lint.py`, #1909); a table still in code gets one entry per line in alphabetical order.
**Before you add an item, key, setting, mode, plugin command, trigger type or data file test, read `docs/extend.md`.**
**No test checks the content of a data or configuration file** (owner): test the form and the behavior, with values
from the data or test data. A change of data files only adds no test (#4242).

## How to verify

No Minecraft window here. From cheap to expensive: lint and the tests of the change → slow tests → `--preview` PNG
(Read tool) → `world_reader.py` → `mc_check.py` → `mc_shot.py`. Details: the `verify` skill.

@framework/CLAUDE.md

@docs/LEARNINGS.md
