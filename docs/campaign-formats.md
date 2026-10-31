# Campaign container formats

This document gives the layout of the AoE2 campaign files and of the old scenario format. The tickets of #149 use it
(#200: `.aoe2campaign`, #201: `.cpx`, #202: README).

## Sources

| Source | What | License |
|---|---|---|
| [genie-rs](https://github.com/SiegeEngineers/genie-rs), crate `genie-cpx` (`crates/genie-cpx/src/read.rs`, `lib.rs`) | Reader and writer of all campaign versions | GPL-3.0 (aoe2mc is GPL-3.0 too) |
| genie-rs, crate `genie-scx` (`crates/genie-scx/src/format.rs`, `header.rs`, `map.rs`) | Reader of all scenario versions, also `.scx` and `.scn` | GPL-3.0 |
| genie-rs test files (`crates/genie-cpx/test/campaigns/`) | Real campaigns: `acam1.aoe2campaign`, `rcam3.aoe2campaign` (DE), `DER FALL VON SACSAHUAMAN - TEIL I.cpx` (AoK) | Game data and a HeavenGames upload: do not copy them into this repository |
| AoE2ScenarioParser 0.9.8 | DE scenarios (`.aoe2scenario`) only. No campaign support | GPL-3.0 |

Check (2026-10-25, #199): a short Python script that reads the layout below. It read `acam1.aoe2campaign` (5 scenarios) and the
`.cpx` (1 scenario) without error. The scenarios fill the file to its last byte. AoE2ScenarioParser 0.9.8 read the
first scenario that the script took out of `acam1.aoe2campaign` (`A1_Tariq1.aoe2scenario`, format `1.36`, map 144,
2956 units).

## Common rules

- All numbers are little-endian.
- A campaign is a container: a header, a table with one entry per scenario, then the scenario files, one after the
  other. Each scenario is a complete scenario file (the same bytes as a file on disk). To extract scenario i, read
  `size` bytes at `offset`.
- The first 4 bytes are the version as ASCII text:

| Version | Game | Extension | Scenario files inside |
|---|---|---|---|
| `1.00` | AoE1, AoK, AoC, AoE2 HD | `.cpn` (AoE1, AoK), `.cpx` (AoC, HD) | `.scn`, `.scx` (old format) |
| `1.10` | AoE1 DE | `.aoecpn` | `.aoescn` |
| `2.00` | AoE2 DE | `.aoe2campaign` | `.aoe2scenario` |

- "Fixed string N": N bytes, the text ends at the first 0 byte. The encoding is not given: old files use the code
  page of the author (genie-rs detects it with `chardet`; for example `Sacsahuam\xe1n` is Windows-1252).
- "DE string": `u16` 0x0A60 (bytes `60 0A`), `u16` length, then the UTF-8 bytes. No 0 byte at the end.

## `.cpx` and `.cpn` (version `1.00`)

| Offset | Type | Field |
|---|---|---|
| 0 | char[4] | version `1.00` |
| 4 | fixed string 256 | campaign name |
| 260 | i32 | number of scenarios n |
| 264 | n × 520 bytes | scenario table |

One entry of the table (520 bytes):

| Offset | Type | Field |
|---|---|---|
| 0 | i32 | size of the scenario file |
| 4 | i32 | offset of the scenario file from the start of the campaign |
| 8 | fixed string 255 | scenario name |
| 263 | fixed string 255 | file name (`.scx` or `.scn`) |
| 518 | 2 bytes | padding |

The first scenario starts at 264 + 520 n (the `.cpx` sample: 784 for n = 1).

## `.aoe2campaign` (version `2.00`)

| Type | Field |
|---|---|
| char[4] | version `2.00` |
| u32 | number of dependencies d |
| d × i32 | DLC dependencies (the sample `acam1`: 2, 3, 4, 5, 6, 7) |
| fixed string 256 | campaign name |
| u32 | number of scenarios n |
| n × entry | scenario table |

One entry of the table (variable size):

| Type | Field |
|---|---|
| u32 | size of the scenario file |
| u32 | offset of the scenario file from the start of the campaign |
| DE string | scenario name |
| DE string | file name (`.aoe2scenario`) |

AoE1 DE (`1.10`, `.aoecpn`) is different: `u32` number of scenarios, then a DE string for the name, and entries with
`u64` size and `u64` offset. aoe2mc does not need it.

## The old scenario format (`.scx`, `.scn`)

The converter needs: map size, terrain, elevation, players (civilization, color) and units (type, position, rotation).
The layout (genie-scx `SCXFormat::read_from`):

1. char[4] format version (`1.21` in the `.cpx` sample, AoC; other games and patches use other numbers, genie-scx
   compares them).
2. Header, not compressed: `u32` header size, `u32` header version, `u32` time stamp (header version ≥ 2),
   description (`u32` length and bytes), `u32` "any single-player victory", `u32` number of active players,
   more fields for header version > 2 (DLC options) and ≥ 5 (author, number of triggers).
3. The rest of the file is compressed with raw deflate (no zlib header: `zlib.decompress(data, -15)` in Python).
   In it, in this order:
   1. `i32` next object ID.
   2. `TribeScen`: the players (names, civilization, AI, resources), messages, cinematics, the bitmap, the victory
      conditions, the diplomacy, the disabled techs and units. Its fields change with the format version: it is
      the largest part of a reader (about 500 lines of Rust in genie-scx).
   3. `Map`: `u32` width, `u32` height (the map versions of HD and DE add a version field and more), then
      width × height tiles. A tile of the old format is 3 bytes: `u8` terrain, `i8` elevation, `i8` zone.
   4. `u32` number of players, the world data of each player (resources, population).
   5. The scenario player data and the objects of each player. Before `1.36` the objects come first:
      for each player `u32` count, then per object `f32` x, `f32` y, `f32` z, `i32` ID, `u16` type, `u8` state,
      `f32` angle, `i16` frame (format ≥ `1.15`), `i32` garrisoned in (format ≥ `1.13`).
   6. Triggers (format ≥ `1.14`) and AI files. The converter does not need them.

`scx.py` (#311) reads format `1.21` and the `.scn` formats `1.18`, `1.19`, `1.20` of The Age of Kings (#3860; the same
object layout; data version 1.14 to 1.27) and the formats `1.22` to `1.26` of the HD Edition (#3862; also as
`.aoe2scenario`: `aoe2mc.read_map` reads the first 4 bytes, and a format of `scx.FORMATS` goes to `read_scx`). The first
DE format is `1.32` (data version 1.28 and later: DE fields); AoE2ScenarioParser reads `1.36` and later: `scx.read(path)` gives the map size, terrain and
elevation (`[x, y]`, as `read_scenario`) and the players (civilization, color, start view). It skips the header with its
size field, skips `TribeScen` field by field, reads the map, skips the world data and the objects, and reads the
scenario player data (the color is there). It also reads the objects (#312): `aoe2mc.read_scx` gives the
result to the pipeline in the form of `read_scenario`, so `aoe2mc.py IN.scx OUT` converts the scenario. A test builds a file byte by byte (`tests/test_scx.py`). A check with the
genie-rs test file `Age of Heroes b1-3-5.scx` (format `1.21`, 200 × 200, not in this repository) read all 8 players,
and the bytes after the player data are the trigger version 1.6.

`scx.py` also reads the first DE formats `1.32` to `1.35` (#5072): AoE2ScenarioParser has no layout before `1.36`, and
6 base scenarios of DE random maps have format `1.33` or `1.35`. In DE the data version is the format. The DE fields of
`TribeScen` (genie-scx `RGEScen` and `TribeScen`): data version ≥ 1.28: 16 `u32` civilization locks before the file
name, and the disabled techs, units and buildings are 16 counts and then lists of that length (not fixed lists); at
the end, ≥ 1.35: `u32` number of triggers, ≥ 1.30: `u16` signature and the water definition, ≥ 1.32: `u16` signature and
the color mood, ≥ 1.36: `u8` "collide and correct", ≥ 1.37: `u8` "villager force drop". The DE map is map version 2
(marker `0xDEADF00D`, version, `u8` "no waves", size, tiles of 7 bytes; AoE2ScenarioParser names the marker and version
`player_1_camera_y` and `player_1_camera_x`). A file of `1.35` differs from `1.36` only by the "collide and correct"
byte and by the order of step 5 (objects first); `1.33` also has no trigger count. A check with the genie-rs test files
`Hotkey Trainer Buildings.aoe2scenario` (`1.36`) and `layertest.aoe2scenario` (`1.37`, not in this repository; the
check allowed these formats for a moment) gave the same terrain, elevation and objects as AoE2ScenarioParser. A test
builds `1.33` and `1.35` files byte by byte (`tests/test_scenario_de_135.py`). The civilization IDs of DE above 18 are
not in `scx_civs.jsonl` (`CIV_36`): a base scenario of a random map needs only the map.

The civilization of a player is in `TribeScen`, so a reader must read all of `TribeScen` to get to the map. The unit
type IDs of the old games are the same IDs as in DE for the units that both have.

## Recommendation

- **`.aoe2campaign` (#200):** read the header and the table, give the bytes of each scenario to AoE2ScenarioParser
  (write them to a temporary file, or use the parser's read from bytes). Test with a campaign that the test builds:
  version `2.00`, 0 dependencies, the scenarios of `tools/scenarios.py`. About 40 lines.
- **`.cpx` (#201):** first a clear message, not a reader. The container is simple: the converter can read the table
  and write each `.scx` file out, then stop with these steps for the user:
  1. Copy the `.scx` files to the scenario folder of AoE2 DE
     (`<Steam user folder>/Games/Age of Empires 2 DE/<id>/resources/_common/scenario`).
  2. In the DE scenario editor, open each scenario and save it (DE saves it as `.aoe2scenario`).
     Or, in the DE campaign editor, make a new campaign of the saved scenarios (`.aoe2campaign`).
  3. Convert the new files with aoe2mc.
  Since #347 the converter converts the `.scx` scenarios of format `1.21` directly (`scx.py`, #311, #312) and gives
  these steps only for the other scenarios.

  The owner must check step 2 in the game (it is not confirmed in a source that the DE editor opens `.scx` files):
  ask in #201 (`needs-human`). A minimal reader of old scenarios is a port of `TribeScen`, `Map` and the objects
  of genie-scx (GPL-3.0 like aoe2mc), about 300 lines of Python and one format version (`1.21`) first.
  Make it a separate ticket after #201, and only if the owner wants it.
- **Samples:** no free `.cpx` sample with a clear license exists. The genie-rs test file is a HeavenGames upload
  (`aok.heavengames.com/blacksmith/showfile.php?fileid=884`) without a license. A test can build a `.cpx`
  container in code (the layout above), with any bytes as the scenario, to test the table and the extraction.
  For a test of a real old scenario, ask the owner for a `.cpx` file (#202 or #201).
