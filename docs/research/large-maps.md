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
