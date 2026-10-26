# Large maps: time and memory of a conversion

Epic #689 (`convert:large`). This document holds the measurements of each conversion phase for a 480 × 480 tile map
("Ludicrous" size). The next tickets of the epic make the slowest phase faster: measure again with the same commands and
add a new table below the old one.

## Method

1. Make the map: `python3 tools/scenarios.py large L.aoe2scenario` (#690). It has smooth hills (elevation 0-4),
   lakes, 28 557 forest trees, and 8 players, each with a town center, 4 houses, 20 villagers, 10 militia, 5 gold
   mines, 5 stone mines and 5 berry bushes. The map is seeded: the same file each run.
2. Measure: `python3 tools/measure_convert.py L.aoe2scenario` (default `--tile-size 4`: 1920 × 1920 blocks,
   14 400 chunks). The conversion runs in the process of the tool. A thread reads the resident memory (RSS) every
   10 ms, and `aoe2mc.TICKS` gives the end of each phase. "units" and "chunks" take turns in the chunk loop: their
   rows add all their parts.
3. Same output: a plain `cmp` of two worlds fails, because the `.mca` header has the write time of each chunk and
   `level.dat` has LastPlayed. Compare the zlib-decompressed chunk payloads of each `.mca` and the gunzipped `.dat`
   files (without `level.dat`). For a fast loop, record the arguments of a sample of `build_chunk` calls with
   `pickle` (also `aoe2mc.B` and `aoe2mc.BLOCK_DATA`: the block IDs depend on them) and time only that function (#701).

## Result 2026-10-26 (#690)

Cloud session: 4 cores, 15 GB memory, Python 3.11, numpy 2.4. One run.

| Phase | Seconds | Share | Peak RSS (MB) |
|---|---|---|---|
| read | 10.2 | 13 % | 490 |
| columns | 1.7 | 2 % | 814 |
| objects | 30.3 | 38 % | 978 |
| units | 0.0 | 0 % | 839 |
| chunks | 35.0 | 44 % | 853 |
| write | 2.6 | 3 % | 1092 |
| total | 79.8 | 100 % | 1092 |

- The slowest phase is "chunks" (35.0 s, 44 %). The chunk loop (`build_chunk`, `write_region`) and `place_objects` take 82 % of the time. Together with "read"
  (10 s for 230 400 tiles and 28 800 objects in AoE2ScenarioParser) they are the targets of the next tickets.
- Peak memory is 1.1 GB: below the 4 GB limit of the epic.

## Result 2026-10-26 (#701): the chunk phase

Same machine type, the same session, before and after the change (a slow-test run was in parallel for both).
`build_chunk` makes the terrain only up to the highest ground or water of the chunk (above it all is air), and the
tall-plant and block-entity scans look only at the sections with blocks. Before, each of the about 15 numpy passes
went over all 384 rows.

| Phase | Before (s) | After (s) | Peak RSS after (MB) |
|---|---|---|---|
| read | 11.1 | 10.7 | 490 |
| columns | 2.7 | 2.5 | 821 |
| objects | 33.7 | 33.9 | 978 |
| units | 0.1 | 0.0 | 841 |
| chunks | 37.0 | 21.7 | 855 |
| write | 3.5 | 3.4 | 1097 |
| total | 88.0 | 72.4 | 1097 |

- "chunks" is 41 % faster (37.0 s → 21.7 s). Now "objects" is the slowest phase (#702).
- Same output: the decompressed chunks and entities of the `tiny`, `stress` and `village` worlds are the same as
  before, and 1240 sampled chunks of the `large` map give the same bytes (only `level.dat` has a new LastPlayed time).

## Result 2026-10-26: one add for each tree and obstacle (#702)

The profile (`python3 -m cProfile`) of the object phase showed 609 460 calls of `Edits.add` (43 of 66 s): 4 to 6 for
each tree (`disc`, `box`) and one for each block column of a barrier (`obstacle`). Now `make_tree` draws each
(kind, height, leaves) shape once (`TREE_SHAPES`, `tree_shape`) and adds it with one call, and `obstacle` adds all
its columns with one call. `Edits.add` takes one `hard` flag for each block. The random numbers and the order of the
blocks stay the same: `tools/world_diff.py` shows the same bytes for `tiny`, `stress`, `village`, `gallery` and `large`.

Same session for both rows. This session was about 2.5 times slower than the session of #690, so compare the rows
with each other, not with the first table. Both rows are without the chunk change of #701 (measured before it merged).

| Phase | Before (s) | After (s) | Change |
|---|---|---|---|
| read | 29.2 | 30.3 | |
| columns | 6.3 | 6.0 | |
| objects | 73.4 | 17.9 | −76 % |
| units | 0.1 | 0.2 | |
| chunks | 88.7 | 100.2 | |
| write | 7.8 | 7.5 | |
| total | 205.6 | 162.1 | −21 % |

Peak memory: 1148 MB before, 972 MB after (fewer small arrays in `Edits.parts`).
