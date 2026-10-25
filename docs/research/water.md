# Research: the height of water in AoE2 (#164)

Part of #155 (water at the height of its terrain, natural shores).

## Questions and answers

1. **One water height per body or per tile?** Per tile. AoE2 has no water level. Each tile has one elevation
   (0–7 in the original game, 0–16 in DE since update 141935, wiki page "Elevation"). The game draws all terrain,
   water too, as one height map. Water on raised tiles is drawn raised and tilted with the slope. Ships and fish stay
   on the terrain surface. Scenario designers use this for "mountain lakes" and sloped "waterfalls". (Source: the
   wiki says that units float at the water surface and the sea floor has its own elevation only in Age of
   Mythology; in AoE2 the terrain has one height map. Not checked on a DE screenshot in this ticket.)
2. **Which value does a body get when its tiles have different elevations?** The game does not choose one. The
   converter must choose, because Minecraft water must be level (else it flows).
3. **How does the game draw water next to higher land?** As a slope of the height map: the edge of the water tile
   rises to the land over one tile. There is never a vertical wall.

## Elevations of the water tiles

`samples/*.aoe2scenario` are synthetic maps (made by `tools/scenarios.py`). Two real DE random maps come from the
test records of the `mgz` parser (`happyleavesaoc/aoc-mgz`, MIT license, `tests/recs/`), read with
`mgz.model.parse_match` (`map.tiles`: terrain, elevation).

| Map | Size | Water tiles | Bodies (4-connected) | Water elevation (min / max / most common) | Elevation of the land next to the water |
|---|---|---|---|---|---|
| `samples/gallery` | 96 | 384 | 1 | 0 / 0 / 0 | 0 (96 tiles) |
| `samples/stress` | 100 | 500 | 1 | 0 / 0 / 0 | 1–7 (23, 32, 28, 29, 41, 29, 18 tiles) |
| `samples/test_village` | 48 | 480 | 1 | 0 / 0 / 0 | 0 (48 tiles) |
| `samples/unit_gallery` | 120 | 2880 | 1 | 0 / 0 / 0 | 0 (120 tiles) |
| DE record `de-64.3` (TTL4 Acropolis v3) | 120 | 180 (`WATER_SHALLOW`) | 1 | 0 / 0 / 0 | 0 (62 tiles) |
| DE record `de-13.34` (Arabia) | 120 | 0 | 0 | – | – |

Result: in all maps here, the water is at elevation 0. The random map generator raises land, not water.
The trench that the owner saw (#155) has two possible causes:
- Land of elevation 1 or more next to the water (as in `samples/stress`): the land is `H` blocks or more above
  the water surface, and the converter has no slope at the shore (the bilinear `upsample` gives only a part of a
  tile). This is the shore ticket (#166).
- Water tiles of elevation 1 or more (scenario maps): the converter puts the water at `WATER_Y` and ignores the
  elevation, so the river lies `elevation × H` blocks below its banks. This is the level ticket (#165).

## Proposal for #165

- Give each 4-connected body of water one surface: `WATER_Y + H × e`, with `e` = the **lowest** elevation of its
  tiles. The lowest value never puts water above the ground of one of its own tiles, so water cannot spill. Tiles of
  a higher elevation in the same body become deeper water; the shore ticket smooths the land around them.
- Count the depth (shallow 1, water 4, deep 7) from this surface. Keep `WATER_Y` as the surface of bodies at
  elevation 0, so maps like the samples do not change.
- Where two bodies at different levels touch, they are not 4-connected (else they are one body); a diagonal touch
  needs a shore block between them.
- A body whose elevations differ a lot (a river down a hill) can get steps with waterfalls in a later ticket.

To test the rule, make a test scenario with `tools/scenarios.py` (a river at elevation 2 between land at elevation
2), because no real map here has raised water.
