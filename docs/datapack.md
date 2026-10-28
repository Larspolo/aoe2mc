# World datapacks: custom biomes and functions

Research for #188 (ambience) in #218. Targets: Minecraft Java 1.21.1 and 26.3.
All facts come from the Mojang data in `misode/mcmeta` (branches `<version>-data` and `<version>-summary`)
and from tests with the real server and client (see "Method").

## Result in short

- A converted world can carry a datapack in `<world>/datapacks/<name>/`. Functions and predicates load without a
  warning. A scheduled function that runs every 2 s costs no measurable tick time.
- **A custom biome makes the client show "Worlds using Experimental Settings are not supported"** each time the
  player opens the world, in 1.21.1 and in 26.3. The player must click "I know what I'm doing!" or "Create Backup
  and Load". A datapack that only overrides a vanilla biome (`data/minecraft/worldgen/biome/plains.json`) gives the
  same warning. Any file in `worldgen/` causes it.
- The biome format is very different in 1.21.1 and 26.3: the converter must write one biome file per version.
- If the player removes the datapack, the world still loads: the server logs "Unknown registry key ... -> using
  default" for each section, and the custom biome becomes `minecraft:plains`.

Recommendation for #219: the owner decides if the warning is acceptable. Without custom biomes, a function can
give most of the effect: `execute at @a if biome ~ ~ ~ minecraft:forest run particle ...` and `playsound`, near
the player, with the vanilla biome that `terrain_style` already selects. Sky, fog and water colors and the
biome's own ambient loop need a custom biome.

## What aoe2mc writes

`write_datapack` in `aoe2mc.py` (#220) writes `datapacks/aoe2mc` when the map has a building with a work sound
(`WORK_SOUNDS`). `pulse.mcfunction` has one line per building at the center of its footprint, at the feet height of
the ground next to it (the median of the cells around the footprint, #588: the ground inside is the roof):
`execute positioned X Y Z if entity @a[distance=..16] if predicate aoe2mc:sometimes run playsound ...`.
`playsound` at volume 1 is heard up to 16 blocks, so the check is not larger.
It uses fixed positions, not marker entities: no entity must load, and the check costs nothing that `/tick query`
shows. The pack has no `worldgen/` file, so the client shows no warning.

Ambience (#219, `AMBIENCE` in `aoe2mc.py`): the pulse also has lines like `execute as @a at @s if biome ~ ~ ~
minecraft:forest run particle ...` and `... playsound ... ambient @s`, for each terrain group (forest, snow, desert,
swamp, water, grass) whose vanilla biomes are in the map. The owner chose (#219): custom biomes only with
`--ambience full`, default `basic` (no `worldgen/` file, no warning). `full` maps the vanilla biomes of a group to
`aoe2mc:<group>` in the chunks and writes `worldgen/biome/<group>.json` in the format of the output version.

Teams (#358, `team_lines` in `aoe2mc.py`): each unit of player N has the tag `aoe2mc.pN` (`units.make_entity`).
`load.mcfunction` makes the team `pN` ("Player N (civilization)") in the nearest chat color of the player color
(`units.TEAM_COLOR`). A load function reaches only the entities of loaded chunks, so the pulse puts each new unit in
its team: `team join pN @e[tag=aoe2mc.pN,team=]`. Gaia has no team. `--ambience off` writes no pack, so no teams.

Timer triggers (#648, `trigger_files` in `aoe2mc.py`, epic #645): a trigger that is enabled at the start and has only
timer conditions gets `function/trigger/<id>.mcfunction`. `load.mcfunction` starts it with
`schedule function aoe2mc:trigger/<id> <20 × largest timer>t replace`. "Send Chat" → `tellraw @a`, "Display
Instructions" → `title @a times` (its display time), `subtitle` and an empty `title`. AoE2 color tags are removed.
A looping trigger schedules itself again.

Area triggers (#649): a trigger with only "Objects in Area" conditions gets a line in `function/tick.mcfunction`
(tag `minecraft:tick`): `execute if entity @e[tag=aoe2mc.p<player>,x=..,y=-64,z=..,dx=..,dy=383,dz=..]` (the blocks of
the tiles, all heights; an area of -1 is the whole map) `unless score #<id> aoe_trig matches 1 run function ...`.
The function sets `#<id>` to 1, so the trigger fires once. A looping trigger resets the score when its units leave an
area, so it fires again when they enter. A quantity above 1 counts the units with `execute store result score`.
A unit type filter (`object_list`) adds `tag=aoe2mc.t<id>`: each unit of a player has the tag of its AoE2 type (#681).
A filter by unit class or group skips the trigger for now. A trigger with other or mixed conditions is not written yet.
Cost: +0.1 ms per tick on the `triggers` scenario (`tools/tick_cost.py`).

Objects (#656): "Create Object" → `summon` of the entity of `units.make_entity` at the middle of the tile, on the
ground, with the tag of the player and no UUID (Minecraft gives a new one). "Remove Object" → `kill` with the area
selector of the area triggers and the mob type; a rider also kills its mount (`execute ... on vehicle`). Buildings and
other objects are not supported yet: the converter counts them ("create (not supported yet)"). The effect tiles and
areas turn with `--orientation`.

## Pack layout

```
<world>/datapacks/aoe2mc/
  pack.mcmeta
  data/minecraft/tags/function/load.json      {"values": ["aoe2mc:load"]}   (runs at each server start)
  data/minecraft/tags/function/tick.json      {"values": ["aoe2mc:tick"]}   (runs each tick: avoid)
  data/aoe2mc/function/<name>.mcfunction      (folder "function", singular, since pack format 45)
  data/aoe2mc/predicate/<name>.json
  data/aoe2mc/worldgen/biome/<name>.json      (causes the experimental warning)
```

| | 1.21.1 | 26.3 |
|---|---|---|
| `pack.mcmeta` | `{"pack": {"description": "...", "pack_format": 48}}` | `{"pack": {"description": "...", "pack_format": 121, "min_format": 121, "max_format": 121}}` |
| Pack format source | `version.json` `data_pack_version` | `data_pack_version` 121, `data_pack_version_minor` 0 |
| Predicate `random_chance` | `{"condition": "minecraft:random_chance", "chance": 0.3}` | `{"type": "minecraft:random_chance", "chance": 0.3}` (`condition` fails: "No key type") |

`level.dat`: the server finds a new pack in `datapacks/` and enables it by itself ("Found new data pack
file/aoe2mc, loading it automatically"). The converter can also add `file/aoe2mc` to `DataPacks.Enabled`; both
work. **An error in any datapack file stops the server** ("Failed to load datapacks, can't proceed with server
load"): each file must pass `tools/mc_check.py` for both versions.

## Biome files

Copy the fields of a vanilla biome (`data/minecraft/worldgen/biome/*.json` in `misode/mcmeta`, branch
`<version>-data`). Minimal files that load without errors (tested; the `ambient_sound` loop is in the vanilla `basalt_deltas`):

1.21.1 (colors are decimal integers; `carvers` is an object; `spawners` and `spawn_costs` are needed):

```json
{"has_precipitation": true, "temperature": 0.7, "downfall": 0.8,
 "effects": {"sky_color": 7907327, "fog_color": 12638463, "water_color": 4159204, "water_fog_color": 329011,
             "grass_color": 5877296, "foliage_color": 3842080,
             "additions_sound": {"sound": "minecraft:entity.parrot.ambient", "tick_chance": 0.005},
             "mood_sound": {"sound": "minecraft:ambient.cave", "tick_delay": 6000, "block_search_extent": 8, "offset": 2.0},
             "particle": {"options": {"type": "minecraft:cherry_leaves"}, "probability": 0.002}},
 "spawners": {}, "spawn_costs": {}, "features": [], "carvers": {}}
```

26.3 (colors are `"#rrggbb"` strings; most effects moved to `attributes`; `carvers` is a list; no `spawners`):

```json
{"has_precipitation": true, "temperature": 0.7, "downfall": 0.8,
 "effects": {"water_color": "#3f76e4", "grass_color": "#59ae30", "foliage_color": "#3aa020"},
 "attributes": {
   "minecraft:visual/sky_color": "#77a8ff", "minecraft:visual/fog_color": "#c0d8ff",
   "minecraft:visual/water_fog_color": "#050533",
   "minecraft:audio/ambient_sounds": {
     "additions": {"sound": "minecraft:entity.parrot.ambient", "tick_chance": 0.005},
     "mood": {"sound": "minecraft:ambient.cave", "tick_delay": 6000, "block_search_extent": 8, "offset": 2.0}},
   "minecraft:visual/ambient_particles": {"modifier": "append", "argument": [
     {"particle": {"type": "minecraft:cherry_leaves"}, "probability": 0.002}]}},
 "features": [], "carvers": []}
```

Map of the 1.21.1 `effects` fields to 26.3:

| 1.21.1 `effects` | 26.3 |
|---|---|
| `sky_color`, `fog_color`, `water_fog_color` | `attributes`: `minecraft:visual/sky_color`, `visual/fog_color`, `visual/water_fog_color` |
| `water_color`, `grass_color`, `foliage_color`, `grass_color_modifier` | stay in `effects` (as `"#rrggbb"`) |
| `ambient_sound`, `additions_sound`, `mood_sound` | `minecraft:audio/ambient_sounds`: `loop`, `additions`, `mood` |
| `particle` (`options`, `probability`) | `minecraft:visual/ambient_particles` (`modifier: append`, list of `particle`, `probability`) |
| `music` | `minecraft:audio/background_music` (`default`) |
| `spawners`, `spawn_costs` | `minecraft:gameplay/natural_mob_spawns` |

26.3 has more environment attributes (registry `environment_attribute` in `registries/data.json`), for example
`visual/fog_start_distance`, `visual/cloud_color`, `visual/sky_light_color`, `visual/sunrise_sunset_color`.
The overworld `dimension_type` sets the defaults; a biome overrides them.

Particle types that need no options and exist in both versions: `cherry_leaves`, `snowflake`, `white_ash`,
`ash`, `spore_blossom_air`, `falling_spore_blossom`, `crimson_spore`, `warped_spore`.

The chunk biome palettes can hold the custom name (`aoe2mc:forest`) directly: `fillbiome` wrote it, and the server
saved and loaded it again without errors. So `build_chunk` can write custom biome names like vanilla names.

## Functions and their cost

Pattern that stays cheap: a `load` function starts a loop with `schedule function aoe2mc:pulse 40t replace`; the
pulse does its work and schedules itself again. Work only near players, for example:

```
execute as @a at @s as @e[type=marker,tag=aoe2mc.smith,distance=..24,sort=random,limit=1] at @s if predicate aoe2mc:sometimes run playsound minecraft:block.anvil.use ambient @a ~ ~ ~ 0.6
```

`marker` entities are invisible, have no hitbox and are not sent to the client. `/tick query` (average of the
last 100 ticks), tiny world, headless server:

| Load | 1.21.1 | 26.3 |
|---|---|---|
| Datapack with the 2 s pulse, no players | 1.6 ms | 1.8 ms |
| 1000 idle markers | 1.5 ms | 1.6 ms |
| 1000 markers, each runs a `particle` command with a 30 % predicate **every tick** | 2.5 ms | 3.0 ms |

The budget is 50 ms per tick. Even the worst case (every tick, 1000 markers) costs about 1 ms. A pulse every
2 s near the players costs nothing that `/tick query` can measure.

The pulse also gives each player the map of the world in the off-hand once (#966): `item replace entity @s
weapon.offhand` for `@a[tag=!aoe2mc_map]`, then the tag `aoe2mc_map`. The tag stays in the player data, so a
player gets the map one time only. `level.dat` `Data.Player` does not work for this: the 26.3 client ignored it
in a single player world (#966).

`python3 tools/tick_cost.py` measures this again on the `village` scenario (#458): a server on the world with and
without `datapacks/aoe2mc`, the median of the `/tick query` means over 60 s. A `mc` test (`tests/test_tick_cost.py`)
fails when the pack costs 2 ms per tick or more. Village, 26.3, no players: 14 pulse lines, 1.00 ms without and
1.15 ms with the pack (`--ambience basic`).

## Method

1. `python3 tools/scenarios.py tiny T.aoe2scenario`, then convert it with `--mc-version 1.21.1` and `26.3`.
2. Copy the world, write the pack, start the server with `tools/mc_check.Server` and send commands through
   stdin: `datapack list`, `fillbiome 32 60 32 47 75 47 aoe2mc:forest` (at most 32768 blocks per command),
   `execute if biome 40 66 40 aoe2mc:forest run say biome ok`, `tick query`, `save-all flush`, `stop`.
3. Load the saved world again with `tools/mc_check.py` (with and without the pack) and read the biome palettes
   with `tools/world_reader.read_region`.
4. Open the world in the real client with `tools/mc_shot.py`. If the client does not reach the view, the tool
   saves the screen that stops it (here the experimental warning). A pack with functions only (the pack of
   `mc_shot.py` itself) opens without the warning.

## Pitfalls

Moved from `docs/LEARNINGS.md` (improve run, 2026-10-26).

- A datapack `load` function or an RCON `@e` selector sees only entities of loaded chunks: 26.3 loads none without a
  player. In an RCON check, `forceload add X0 Z0 X1 Z1` (at most 256 chunks per command) first (#358).
- RCON `execute if entity SEL` answers "Test passed. Count: N" (capital C) or "Test failed": match with `re.I` (#676).
- A timer trigger fires from the server start, before a client joins (about 30 s). To see its chat in a client
  (`mc_shot.Client`), send `tick freeze` first and `tick unfreeze` after the join: the `schedule` timers wait, and
  the chunks and entities load in a frozen game (#676).
- A new player gets an item through the datapack pulse (`item replace entity @s weapon.offhand`, a tag against
  repeats), not through `Data.Player` of `level.dat`: the 26.3 client ignored a `Player` tag that the converter
  wrote (#966). The datapack also works on a server, where `level.dat` has no player.
- A unit in a chunk that is not loaded is no entity for a command: `execute unless entity @e[tag=X]` is true before a
  player comes near, so a "unit is dead" test fired at once on a server with no player (#2618). Test the absence only
  where the unit was: a `marker` entity that follows the unit each tick is not loaded either (`OBJECT_TESTS`).
- A predicate file of 26.3 names its kind with the key `"type"` (`"minecraft:entity_properties"`), not the older
  `"condition"`, and an entity predicate has namespaced keys: `{"minecraft:vehicle": {"minecraft:entity_type": [...]}}`,
  not `"vehicle"`, `"type"`. Else the server says "Failed to load datapacks" and never prints "Done", so a `-m mc`
  test waits 300 s for nothing (#2976). Read `logs/latest.log` of the server directory for the cause; copy the form
  from a vanilla file of mcmeta `26.3-data` (`data/minecraft/loot_table/entities/zombie.json` has a vehicle).
