# Minecraft format changes from 1.21.1 to 26.3

aoe2mc wrote Minecraft Java 1.21.1 (data version 3955) until #58; then 26.3 was the default and `--mc-version 1.21.1`
wrote the old format. Since #427 aoe2mc writes only 26.3: this document is the history. It lists the format changes up to 26.3
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
| 1.21.5 to 26.3 | Item component `minecraft:dyed_color` is a plain int (`255`), not `{rgb: 255}`. 26.3 does not load an entity with the old form ("Serialization errors" in the log). | `units.armor_items()` (dyed leather armor) |
| 26.3 | `AngerTime` (ticks) is read, but the game saves `anger_end_time` (Long, game time of the end). | `units.ANGRY` (angry wolves, polar bears) |
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
| 26.1 | The world border (`BorderCenterX`, `BorderSize` ... in `level.dat`) moves to `dimensions/minecraft/overworld/data/minecraft/world_border.dat`: `{data: {center_x, center_z, size, lerp_target, safe_zone, damage_per_block: double, lerp_time: long, warning_blocks, warning_time: int}, DataVersion: N}` (found with `strings` on the data fixers `LegacyWorldBorderFix.class` and `DimensionStorageFileFix.class` in `META-INF/versions/26.3/server-26.3.jar` of the server jar, which is not obfuscated; checked with `worldborder get`, #172). | `write_level_dat()` |

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

## Fog

Research of #1597 (26.3, real server and client). The fog distances are environment attributes:
`minecraft:visual/fog_start_distance`, `fog_end_distance`, `sky_fog_end_distance` (and `fog_color`). A datapack can set
them in a dimension type, a biome or a timeline (`timeline` registry, tag `#minecraft:in_overworld`, which the overworld
dimension type names in `timelines`).

- All three are worldgen registries: a datapack entry in any of them makes the single player client warn
  "Worlds using Experimental Settings are not supported" (dimension type #1150, biome #218, timeline #1597).
- No command sets an environment attribute. `/posteffect` (new in 26.x) has only `blur`, `creeper`,
  `entity_outline`, `invert` and `spider`: no fog.
- A timeline works without changing a vanilla file: `data/aoe2mc/timeline/fog.json` with `"clock": "minecraft:overworld"`
  and one keyframe at tick 0 per track (`{"keyframes": [{"ticks": 0, "value": 4.0}]}`), plus
  `data/minecraft/tags/timeline/in_overworld.json` with `{"values": ["aoe2mc:fog"]}`. Fog from 4 to 48 blocks gave a
  thick haze. `tools/mc_check.py` loads it with no error, and a client that joins a server (vanilla or Paper) gets the
  fog with no warning. The owner chooses where the converter uses it (#1625).

## Not checked

- Book, sign and banner texts: aoe2mc does not write them now. Their text components are NBT since 1.21.5,
  as `CustomName`.
- Items in containers: aoe2mc does not write them now.
- Whether 26.3 opens a world with data version 5023 and the old palette form (`Name`, `Properties`). aoe2mc
  writes `id` and `properties` for 26.3. Its tiny, units gallery and full gallery worlds load in the 26.3 server
  without problems (`tools/mc_check.py --version 26.3`, #57).

## Pitfalls

Moved from `docs/LEARNINGS.md` (improve run, 2026-10-26).

- Minecraft server: a bad property value (`facing=up`) loads silently as the default state. An unknown block gives
  "Recoverable errors when loading section", an unknown block entity id "Skipping block entity with invalid type"
  (26.3 has no `bed` block entity, #249). A missing `level.dat` compound gives "key missing: <name>" (#60). A bad
  datapack file stops the server. A datapack `worldgen/` file makes the client warn "Experimental Settings" (#218).
  The 26.3 server writes a missing `white-list` as `true`: write `white-list=false` (`game/run.py`, #285).
- Minecraft client (#178, #179): `tools/mc_shot.py` runs it in `Xvfb`. 26.3 needs `mesa-vulkan-drivers` (lavapipe) and
  a placeholder for the title panorama. The view ends at about 100 blocks: put `--at` near the subject (#208).
- The server drops entity tags that it does not know, without a log line: let the server save the world and compare
  the entity NBT (`docs/minecraft-versions.md`). A wrong tag type gives "Serialization errors" (`mc_check.py`).
  New entity NBT: convert a map with one unit per type (`add_unit` in a loop) and run `tools/mc_check.py` (1 min).
- PrismarineJS `data/pc/common/protocolVersions.json` has the data versions of all releases (26.3 = 5023).
- An invalid item in a block entity can vanish without a log line. `tools/mc_check.py W --keep DIR` keeps the saved world
  (#27). 26.3 saves a default state as the bare name and in another property order: normalize before you compare (#189).
- 26.3 `particle minecraft:block{block_state:...}`: a block id string or `{id:"minecraft:wheat",Properties:{age:"7"}}`;
  `Name` and `wheat[age=7]` fail ("No key id"). A wrong property value passes silently. `rotate UUID facing X Y Z`
  turns a NoAI mob. Sound names: `registries/data.json` `sound_event` of `misode/mcmeta` `26.3-summary` (#592).
- A world that the Paper server saved does not open in the vanilla client ("Overworld settings missing"): Paper moves
  `data/minecraft/world_gen_settings.dat` into each dimension folder. Copy the `.dat` files of `data/minecraft/` of a fresh
  conversion into the saved copy before `tools/mc_shot.py` (#420, #580).
- The entity tag `Invisible` is only for armor stands (and item frames): the server drops it on a slime or another mob
  without an error (#636). Hide a mob with `active_effects:[{id:"minecraft:invisibility",duration:-1,show_particles:0b}]`.
  A spectator sees invisible mobs: check them with `tools/mc_shot.py --player` (adventure mode).
- A world that the Paper server of `game/run.py` opened fails `tools/mc_check.py` ("Missing data pack paper",
  "Overworld settings missing"): Paper changes `level.dat`. Convert again before a vanilla check (#656).
- RCON `data get entity U CustomName` cuts deep compounds (`{extra: [{...}, " ", {...`): read one part with a path,
  for example `CustomName.extra[2].text`. The answer starts with the display name of the entity (#661).
- A mob with AI has no `NoAI` tag: `data get entity U NoAI` answers "Found no elements matching NoAI", not `0b`. Test for `1b` only (#811).
- Paths of saved data files in 26.3: `strings` on `net/minecraft/util/filefix/fixes/DimensionStorageFileFix.class` of the server jar. Maps: `data/minecraft/maps/N.dat` and `last_id.dat` (`{data: {map: N}}`), not `data/map_N.dat` and `idcounts.dat`. The map colors: `MapColor.class` (`javap -c`, #838).
- A villager with an empty trade list (`Offers:{Recipes:[]}`) saves no `Offers`: `data get entity U Offers.Recipes` answers "Found no elements". A right click on it opens no trade menu, and `talked_to_villager` still counts. A new profession (`data merge` of `VillagerData`) clears the trades: set `Offers` in the same merge (#988).
- The block tags of 26.3 (`#minecraft:replaceable` has air and short plants, not mushrooms, flowers or carpets) are in the inner jar: `unzip -p ~/.cache/aoe2mc/paper/26.3/cache/mojang_26.3.jar META-INF/versions/26.3/server-26.3.jar`, then `data/minecraft/tags/block/NAME.json` (#1124). A `fill` over a chunk that no player loads answers "That position is not loaded": `forceload add` the area in a server check without a player.
- `forceload add` with float coordinates (`1.5`) loads no chunk: a `summon` there fails silently and a UUID selector finds no unit (#1107). Give it integer block coordinates.
- `tools/mc_shot.py` starts the client at render distance 8 (`OPTIONS`): its fog starts at about 115 blocks, so a far view (the replay overview) looks hazy in its images but clear at the vanilla default 12 (#1150). For a far view set `mc_shot.OPTIONS = mc_shot.OPTIONS | {"renderDistance": "12"}` and name the distance in the check.
- A datapack `dimension_type/overworld.json` with `visual/fog_start_distance` also makes the client warn "Experimental Settings" (as a `worldgen/` file), and on Paper it gave no visible change of the distance fog (#1150).
- Two `mc_shot.Client` shots of the same view differ in the sky: the software renderer draws it with a diagonal dither that moves in each frame (#1538). Compare images by the mean of 16 × 16 cells (`Image.resize(..., Image.BOX)`), not pixel by pixel, and crop away the toasts (top right), the sidebar and the map. A translucent (friendly invisible) mob shows clearly only against the sky.
- An inline predicate of `execute if predicate {...}` in 26.3 takes `type:`, not `condition:` ("Failed to parse structure: No key type"). A `-m mc` test that looks for bad answers must also look for "Failed to parse" (#1596, #1633). Rain: `execute if predicate {type:"minecraft:weather_check",raining:true}`.
- `tools/mc_shot.py` (single player) stopped at the "Experimental Settings" screen of a `--fog` world: "Loaded N advancements" is the last client log line. It now presses Tab, Tab and Enter ("I Know What I'm Doing!") 15 s after that line (#1641). A `Client` on the Paper server gets no warning.
- The answer of `data get entity U PATH` cuts a long NBT text after about 140 characters ("..."), and the order of the `attributes` list changes from run to run: a test that looks for a value in a list misses it in some runs (#1713). Ask for one item: `Passengers[0].attributes[{id:"minecraft:max_health"}].base`.
- `data get entity U Color` answers "Sheep has the following entity data: 11b": with a path the answer has the value only, not "Color: 11b" (#1792).
- `tp P X Y Z facing A B C` turns the player so that the ray from the feet hits (A, B, C), not the ray of the eyes: for a click on a unit with `mc_shot.Client`, aim at B - 1.62, else the ray of `Gather.click` passes 1.6 blocks above a small ship. A player in adventure mode falls after the `tp`: `attribute P minecraft:gravity base set 0` (#1666).
- A tag at its default value is not saved: `data get entity U CustomNameVisible` answers "Found no elements matching CustomNameVisible" when it is false. Test with `not ...endswith("1b")` (#1811).
- The world border hurts only players: a zombie and a slime outside it keep their health (Paper 26.3, #2439). The time of `worldborder set <width> <time>` is in ticks: `5` is 0.25 s, write `5s` for seconds.
- An inline item modifier of `item modify` names its function with the key `type` in 26.3 (`{type:"minecraft:set_written_book_pages",mode:"append",pages:[...]}`): the key `function` gives "No key type in MapLike" (Paper 26.3, #2541). A command longer than `rcon.MAX` can append the rest of a written book this way.
- A `mc_shot.Client` player in spectator mode shows no hand items: the map item in the off-hand is not in the image. Use `gamemode creative` and pitch 50 (the map at the lower left, #2581).
- The 26.3 sound event names are the list `"sounds"` of `tools/mcdata/26.3.json` (from `"sound_event"` of mcmeta `26.3-summary/registries/data.json`, #2644): check a new `playsound` name with `mcvalid.sound_error` (#2662).
- 26.x reads the world resource pack from `<world>/resourcepacks/resources.zip`, not `<world>/resources.zip` (#2738, `docs/resourcepack.md`).
- A `mc_shot.Client` player in creative mode falls after a `tp` into the air (no flight): a right click from above hits the ground, not the building. For a real click on a building, `tp` the player onto the ground near it, then `execute as P at @s run tp @s ~ ~ ~ facing X Y Z` (#2805).
- The server cuts the RCON answer of `scoreboard objectives list` after about 150 characters (`[aoe_map_z...`): test one objective with `scoreboard objectives add NAME ...` ("already exists"). A zombie in the open sky burns in daytime (1 damage each second, also with `NoAI`): a server test that counts damage sets `time set midnight` (#2965).
- The `mc_shot.Client` of the cloud has placeholder asset objects (`placeholder_images`: the sandbox blocks resources.download.minecraft.net), so `unifont.zip` is missing: each glyph that only Unifont has (`▂` to `▇`, all text in `minecraft:uniform`) draws as a box. That is no game bug (#3730, check #3449). Also: a replay writes into its world folder; use a fresh copy of the world for each check run, else old text displays stay.
- A `mc_shot.Client` player in creative mode after spectator mode flies: Shift then means "fly down", not sneak, and `gather.SNEAK` fails. Use survival mode after a spectator screenshot. Feet inside a block also lose the sneak pose: `aims()` stands the player on the ground (#3884).
- `pytest -m mc -n 5` on the 4 CPUs of a cloud session: 4 of 5 Paper servers died at the start ("the server stopped"); the same tests passed one at a time. Run at most `-n 2` server tests there (#4589).
