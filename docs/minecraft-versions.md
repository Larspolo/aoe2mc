# Minecraft format changes from 1.21.1 to 26.3

aoe2mc wrote Minecraft Java 1.21.1 (data version 3955) until #58; now 26.3 is the default and `--mc-version 1.21.1`
writes the old format. This document lists the format changes up to 26.3
(data version 5023) that affect the output of aoe2mc. The sub-issues of #14 use it.

## Method

All facts below come from primary data, not from memory:

1. **Registries and block states**: the data reports of Mojang, as JSON in the
   [misode/mcmeta](https://github.com/misode/mcmeta) repository (branches `<version>-summary`, files
   `blocks/data.json` and `registries/data.json`). They were compared for all names that aoe2mc writes: the
   block states of a gallery conversion, of all 9 architecture sets and of all terrains, the 27 entity types,
   the 9 block entity types and the 19 biomes.
2. **Upgrade by the real game**: the dedicated servers of 1.21.2, 1.21.4, 1.21.5, 1.21.11, 26.1, 26.2 and 26.3
   upgraded two aoe2mc worlds (`tools/scenarios.py tiny` and `gallery --kinds U`, which has all entity types)
   with `--forceUpgrade`. The NBT before and after the upgrade was compared. The first version that shows a
   change is the version in the tables. A change can come from a release between two tested versions: then
   the table gives the range.
3. **A native 26.3 world**: the 26.3 server generated a normal world. It shows how 26.3 itself writes the
   files (not only what the upgrade code writes).

Server jars: `piston-meta.mojang.com/mc/game/version_manifest_v2.json` → version JSON → `downloads.server`.
26.x needs Java 25 (`apt-get install openjdk-25-jre-headless`), 1.21.x needs Java 21.

## Data versions

| Release | Date | Data version |
|---|---|---|
| 1.21.1 | 2024-08-08 | 3955 |
| 1.21.2 | 2024-10-22 | 4080 |
| 1.21.3 | 2024-10-23 | 4082 |
| 1.21.4 | 2024-12-03 | 4189 |
| 1.21.5 | 2025-03-25 | 4325 |
| 1.21.6 | 2025-06-17 | 4435 |
| 1.21.7 | 2025-06-30 | 4438 |
| 1.21.8 | 2025-07-17 | 4440 |
| 1.21.9 | 2025-09-30 | 4554 |
| 1.21.10 | 2025-10-07 | 4556 |
| 1.21.11 | 2025-12-09 | 4671 |
| 26.1 | 2026-03-24 | 4786 |
| 26.1.1 | 2026-04-01 | 4788 |
| 26.1.2 | 2026-04-09 | 4790 |
| 26.2 | 2026-06-16 | 4903 |
| 26.3 | 2026-09-15 | 5023 |

Sources: dates from the Mojang version manifest, data versions from PrismarineJS
[`protocolVersions.json`](https://github.com/PrismarineJS/minecraft-data/blob/master/data/pc/common/protocolVersions.json).
mcmeta `26.3-summary/version.json` confirms 5023.

## Blocks, block entities, biomes

| Version | Change | Affects |
|---|---|---|
| 1.21.9 | `chain` is now `iron_chain` (copper chains are new). The properties do not change. | All designs in `buildings.py` that use `chain` |

All other block states that aoe2mc writes (355 states) have the same names and properties in 26.3. All 9 block
entity types (`banner`, `barrel`, `bell`, `blast_furnace`, `campfire`, `chest`, `decorated_pot`, `sign`,
`smoker`) and all 19 biomes exist in 26.3. aoe2mc writes only `id`, `x`, `y`, `z` and `keepPacked` in its block
entities, and the upgrade does not change these.

## Entities

| Version | Change | Affects |
|---|---|---|
| 1.21.2 | `boat` and `chest_boat` are gone. Each wood has its own entity type: `oak_boat`, `spruce_chest_boat`, ... Bamboo is `bamboo_raft` and `bamboo_chest_raft`. The `Type` tag is not used. | `units.boat()`, `units.is_boat()` |
| 1.21.5 | Mob equipment is one compound `equipment` with the keys `head`, `chest`, `legs`, `feet`, `mainhand`, `offhand`, `body`, `saddle`. It replaces `ArmorItems`, `HandItems`, `body_armor_item` and `SaddleItem`. The item format (`id`, `count`, `components`) does not change: the unbreakable helmet keeps `components: {"minecraft:unbreakable": {}}`. | `units.armor()`, `units.hands()`, `units.soldier()`, `units.mounted()` |
| 1.21.5 | Text components are NBT, not JSON strings. `CustomName` is a compound such as `{text: "Zebra", color: "#E0281E"}`. | `units.make_entity()` |
| 1.21.5 | `FallDistance` (float) is now `fall_distance` (double). | `units.to_nbt()` |
| 1.21.5 to 26.3 | Item component `minecraft:dyed_color` is a plain int (`255`), not `{rgb: 255}`. 26.3 does not load an entity with the old form ("Serialization errors" in the log). | `units.item_to_version()` (dyed leather armor) |
| 26.3 | `AngerTime` (ticks) is read, but the game saves `anger_end_time` (Long, game time of the end). | `units.to_version()` (angry wolves, polar bears) |
| 1.21.5 | The upgrade adds `drop_chances: {saddle: 2.0f}` to a saddled mount (the saddle always drops). | Optional: `units.mounted()` |

These tags that aoe2mc writes do not change up to 26.3: `id`, `Pos`, `Motion`, `Rotation`, `UUID`, `Fire`, `Air`,
`OnGround`, `Invulnerable`, `PortalCooldown`, `NoAI`, `PersistenceRequired`, `Silent`, `CustomNameVisible`,
`Passengers`, `Tame`, `ChestedHorse`, `Variant` (horse, llama), `Color` (sheep), `Type` (fox),
`CannotBeHunted`, `IsImmuneToZombification`, `VillagerData`, `Xp`. The upgrade adds `VillagerDataFinalized: 1b`
to villagers; a new writer can add it too.

The upgrade keeps old tags that it does not know (for example `ArmorItems` next to `equipment`, and `Type` on
boats). The game ignores them. A 26.3 writer must not write them.

## Chunks and regions

| Version | Change | Affects |
|---|---|---|
| 26.3 | The block palette has a new form. A block without properties is a string (`"minecraft:stone"`). A block with properties is a compound `{id: "minecraft:tall_grass", properties: {half: "lower"}}` (not `Name` and `Properties`). A list that mixes the two forms wraps each string in a compound with an empty key (`{"": "minecraft:stone"}`). The biome palette stays a list of strings. | `build_chunk()` (section palette) |

The 26.3 upgrade writes all palette entries as compounds with `id` (and `properties`). The 26.3 game reads
this form, so a writer can use it for all entries and does not need the mixed list. 26.2 still writes `Name`
and `Properties`.

The top-level chunk fields of a native 26.3 chunk are the same as in 1.21.1: `DataVersion`, `xPos`, `yPos`,
`zPos`, `Status`, `LastUpdate`, `InhabitedTime`, `isLightOn`, `sections`, `block_entities`, `Heightmaps`,
`block_ticks`, `fluid_ticks`, `structures`, `PostProcessing`. Upgraded chunks also get `blending_data`; a new
writer does not need it. Entity chunks keep `DataVersion`, `Position` and `Entities`. The region file format
(`.mca`) does not change.

## World folder and level.dat

| Version | Change | Affects |
|---|---|---|
| 1.21.6 to 1.21.11 | Game rules have new names in snake case with a namespace and typed values: `doDaylightCycle: "false"` is now `minecraft:advance_time: 0b`, `doWeatherCycle` is `minecraft:advance_weather`, `doMobSpawning` is `minecraft:spawn_mobs`, `doFireTick: "false"` is `minecraft:fire_spread_radius_around_player: 0`. | `write_level_dat()` |
| 1.21.6 to 1.21.11 | The spawn is one compound `spawn: {pos: [I; x, y, z], dimension: "minecraft:overworld", yaw: 0f, pitch: 0f}`. It replaces `SpawnX`, `SpawnY`, `SpawnZ` and `SpawnAngle`. | `write_level_dat()` |
| 26.1 | The overworld moves from `region/` and `entities/` to `dimensions/minecraft/overworld/region/` and `.../entities/`. The Nether and the End move to `dimensions/minecraft/the_nether/` and `.../the_end/`. `playerdata/` is now `players/data/`. | `convert()` (output paths), `tools/world_reader.py`, tests |
| 26.1 | Most fields leave `level.dat`. They go to files in `data/minecraft/`: `game_rules.dat`, `world_gen_settings.dat`, `weather.dat` (`raining`, `thundering`, `rain_time`, `thunder_time`, `clear_weather_time`), `world_clocks.dat` (`minecraft:overworld: {total_ticks, paused}`, was `DayTime`), and others. Each file has the form `{data: {...}, DataVersion: N}`. | `write_level_dat()` |
| 26.1 | `Difficulty` and `hardcore` are now `difficulty_settings: {difficulty: "easy", hardcore: 0b, locked: 0b}`. | `write_level_dat()` |
| 26.1 | The world border (`BorderCenterX`, `BorderSize` ... in `level.dat`) moves to `dimensions/minecraft/overworld/data/minecraft/world_border.dat`: `{data: {center_x, center_z, size, lerp_target, safe_zone, damage_per_block: double, lerp_time: long, warning_blocks, warning_time: int}, DataVersion: N}` (server classes `LegacyWorldBorderFix`, `DimensionStorageFileFix`; checked with `worldborder get`, #172). | `write_level_dat()` |

`level.dat` of a native 26.3 world has only: `DataVersion`, `version`, `Version` (`Id`, `Name`, `Series`,
`Snapshot`), `LevelName`, `GameType`, `allowCommands`, `initialized`, `LastPlayed`, `Time`, `WasModded`,
`ServerBrands`, `version_history`, `spawn`, `difficulty_settings`, `DataPacks`.

The 26.3 game moves the files of an old world itself ("Applying file structure changes" in the log). It is not
known if it does this for a world that has data version 5023 and the old layout. A 26.3 writer must write the
new layout.

Notes for the check of a world with the dedicated server:
- The server writes `gamemode` and `difficulty` from `server.properties` into the world. A changed `GameType`
  after a server run is not a format change.
- The world icon stays `icon.png` in the world folder.

## Not checked

- Book, sign and banner texts: aoe2mc does not write them now. Their text components are NBT since 1.21.5,
  as `CustomName`.
- Items in containers: aoe2mc does not write them now.
- Whether 26.3 opens a world with data version 5023 and the old palette form (`Name`, `Properties`). aoe2mc
  writes `id` and `properties` for 26.3. Its tiny, units gallery and full gallery worlds load in the 26.3 server
  without problems (`tools/mc_check.py --version 26.3`, #57).
