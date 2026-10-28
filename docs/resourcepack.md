# World resource pack (`--resource-pack`)

The converter option `--resource-pack` (#2738, epic #2737) writes a resource pack into the world folder. Single
player loads it with the world. Without the option, the world is the same as before (`tools/world_diff.py`: "same").

## Layout

```
<world>/resourcepacks/resources.zip
    pack.mcmeta
    assets/minecraft/textures/entity/horse/horse_skeleton.png
    assets/minecraft/textures/entity/skeleton/skeleton.png
    assets/minecraft/textures/entity/zombie/drowned.png
    assets/minecraft/textures/entity/zombie/drowned_outer_layer.png
    assets/minecraft/textures/entity/zombie/husk.png
    assets/minecraft/textures/entity/zombie/zombie.png
    assets/minecraft/textures/entity/zombie_villager/zombie_villager.png
    assets/aoe2mc/items/<weapon>.json          (#2744: one for each weapon of data/weapons.jsonl)
    assets/aoe2mc/models/item/<weapon>.json
    assets/aoe2mc/textures/item/<weapon>.png
    assets/minecraft/items/chest.json                (#2746)
    assets/aoe2mc/models/item/war_wagon.json         (#2746)
    assets/aoe2mc/equipment/<unit>.json
    assets/aoe2mc/textures/entity/equipment/humanoid/<unit>.png, <unit>_overlay.png
    assets/aoe2mc/textures/entity/equipment/humanoid_leggings/<unit>.png, <unit>_overlay.png
```

- `pack.mcmeta`: `pack_format`, `min_format` and `max_format` are `VERSIONS[...]["resource_format"]` in `aoe2mc.py`
  (26.3: 97, from `"pack_version"` `"resource_major"` in `version.json` of the client jar; `resource_minor` is 1).
- The textures are 64 × 64 entity textures. `aoe2mc.skin_texture()` draws them with code (no copy of Mojang or AoE2
  files): each box of the model (`SKIN_BOXES`, u, v, w, h, d) gets the color of its part on its six faces (a box puts
  its top and bottom at (u + d, v), its four sides at (u, v + d)), the head gets hair, the front of the head eyes,
  brows and a mouth. The skin tone comes from `SKINS` (a husk is darker).
- The zombie model uses only the top half (64 × 32): the left arm and leg mirror the right ones. The zombie villager
  has a 8 × 10 × 8 head, a nose box at (24, 0), and its clothes come from the overlays `zombie_villager/type/*.png`
  and `profession/*.png`, which the pack does not change.
- The archers (`skeleton`), skirmishers (`drowned`) and cavalry archer horses (`skeleton_horse`) get a human look
  too (#2752). The skeleton texture is 64 × 32 (`SKIN_SIZE`) with 2 wide arms and legs: the model keeps its thin
  limbs. The drowned model has its own left arm (32, 48) and leg (16, 48), and `drowned_outer_layer.png` is empty (no
  seaweed). The skeleton horse uses the horse model: one brown coat on the whole texture and the eyes at (3, 21) and
  (16, 21) (`HORSE_EYES`).
- The cart of the War Wagon (#2746) is a vanilla `chest` item with the `custom_model_data` string `aoe2mc:war_wagon`
  (`units.cart`). `items/chest.json` selects the cart model for it and keeps the vanilla chest definition
  (`VANILLA_CHEST`, from the 26.3 client jar) as the fallback. So the entity is the same with and without the pack.
- A model box out of 0..16 pixels needs an explicit `uv` on each face: else the face reads its texture from the
  neighbors in the atlas (`cart_model`).
- The zip has the same bytes for each conversion: sorted names and a fixed time (a release holds the same bytes).

## Unit armor (#2742)

- Each unit of `data/looks.jsonl` (the infantry of `data/lines.jsonl` and the Spearman line) has one line: `"pattern"`
  (`cloth`, `quilted`, `mail`, `scale`, `plate`), `"accent"` (belt, tabard stripe, helmet band) and `"crest"` (optional).
- With the option, `units.ASSETS` is on, and `units.wear()` gives each armor piece of the unit the component
  `minecraft:equippable` with its slot and `asset_id` `aoe2mc:<name>` (`ELITE_X` wears the asset of `X`). The game
  program (`run.Game`) sets `units.ASSETS` when the world has `resourcepacks/resources.zip`.
- The pack has `assets/aoe2mc/equipment/<name>.json` with the layers `humanoid` and `humanoid_leggings`: a dyeable
  base (`color_when_undyed` white: a dyed leather piece takes the `dyed_color` of its item) and an overlay that is not
  dyed. `aoe2mc.armor_textures()` draws the 64 × 32 textures (`ARMOR_BOXES`) from the material of each piece of the
  unit and the pattern of its look.

## Archers, riders and horses (#2743)

- Each unit with armor has its own asset, not only the units of `data/looks.jsonl`: `units.dressed()` lists the AoE2
  units and heroes (AoE2ScenarioParser `UnitInfo`, `HeroInfo`) and the names of `data/units.jsonl` whose description has
  an armor piece. With `units.ASSETS`, `units.classify()` gives each piece of each mob of the unit (the rider of a
  mount too, `units.pieces()`) the asset `aoe2mc:<name>`. `units.describe()` is the description with vanilla armor.
- The horse armor of a mount (slot `body`) gets the same asset; the pack adds the layer `horse_body` (64 × 64,
  `HORSE_BOXES`: the body, the neck and the head of the horse, with a hem in the accent color; the legs stay bare).
- `data/looks.jsonl` has lines for the main archer, skirmisher, cavalry archer, cavalry and camel lines. Another unit
  takes the look of its hero base (`HERO_BASE`) or a pattern from the material of its chestplate (`units.look()`,
  `DEFAULT_LOOK`). A unit with no own line shares the textures of the same look and materials (`look_<hash>.png`), so
  the pack stays small (about 300 kB for 543 units).

## Weapons (#2744)

- With the option, `units.make_entity` gives each hand item of a unit (also of its rider and crew) the component
  `minecraft:item_model` `aoe2mc:<weapon>` (`units.weapon_models`). The item id stays: the mob fights with it (a bow
  shoots, a crossbow loads). `data/weapons.jsonl`: a part of the unit name (upper case, main hand only) or a vanilla
  item (lower case: the item or its last word, `iron_sword` -> `sword`); the first line that matches wins.
- `units.ASSETS` (#2742) switches it on: `convert` sets it from the option, `game/run.Game` when the world has the pack
  (trained units get the same items).
- The models are flat 16 × 16 items (`item/handheld`, the shield `item/generated`), drawn by `aoe2mc.weapon_texture()`
  from `WEAPON_ART` on the diagonal of the vanilla tools.

## Client behavior (26.3, checked with `tools/mc_shot.py`)

- Single player (`--quickPlaySingleplayer`) loads the pack with no prompt: the log shows
  `Reloading ResourceManager: vanilla, vanilla, server/00000000/<uuid>` after the world loads.
- A pack that fails to load gives the prompt `multiplayer.texturePrompt.failure` (`WorldOpenFlows`).
- Multiplayer (`game/run.py`, #2740): `run.PackServer` serves the zip over HTTP on 127.0.0.1 (a free port), and
  `server.properties` gets `resource-pack`, `resource-pack-sha1`, `require-resource-pack=true` and
  `resource-pack-prompt` (`run.PROMPT`). Before the join the client shows "This server requires the use of a custom
  resource pack." with the prompt text and the buttons "Proceed" and "Disconnect". `mc_shot.Client` at 1280 × 720:
  click (407, 488) for "Proceed"; the player is in `list` only after it.
- Release (#2741): `bundles.yml` builds the pack once (`packaging/release_pack.py`, the bytes of the world pack) as
  `aoe2mc-resourcepack.zip`, and `installers.yml` attaches it to the release of a tag. On a tag each bundle gets
  `release.json` (the tag and the SHA-1 of that pack). The game program of the bundle (`run.pack_source`) then sends
  the release link, when the world pack has that SHA-1; else (a world of another version, a run from the source) it
  uses the local `PackServer`.

## Cost (#2747)

Measured on 2026-10-28 on the `battle` scenario of `tools/scenarios.py` (about 60 units, 256 × 256 blocks), the same
world without and with `--resource-pack`, Minecraft 26.3. The help of `--resource-pack` and the launcher check box
(`gui.PACK_TEXT`) show these numbers: change them together (`tests/test_resourcepack_cost.py`).

| Measure | Without the pack | With the pack | Difference |
|---|---|---|---|
| `resources.zip` size | 0 MB | 4.8 MB | +4.8 MB (`ZIP_STORED`: no compression, see "Pitfalls") |
| Download from the local HTTP server of the game program | - | 0.01 s | at 10 Mbit/s about 4 s, once per world |
| Server tick time, mean (`tools/tick_cost.py --world`) | 3.2 ms | 3.1 ms | none (noise): the same entities, the pack changes only the client |
| Client frame time, median | 94.6 ms | 95.8 ms | +1 % |
| Client frame time, P95 | 115.6 ms | 119.5 ms | +3 % |

Method, to measure again:
1. `python3 tools/pack_cost.py --seconds 20 --out DIR`: the size, the local download time and the client frame times.
   It opens each world in the real client in single player, 12 blocks above the spawn, looks down at the units, and
   runs the vanilla debug profiler (F3 + L). `DIR/without.png` and `DIR/with.png` show the view: check that the pack
   is on. The client draws in software under Xvfb (5 to 10 frames per second): only the difference counts.
2. `python3 tools/tick_cost.py --world DIR/without` and `--world DIR/with`: the line "with the pack" of each is the
   server tick time of the world with its data pack.
3. The world has the same entities with and without the pack (`world_reader`: 239 in both): the armor, the weapons
   and the cart are item components and models, so the server does the same work.

## Pitfalls

- 26.x reads the world pack from `<world>/resourcepacks/resources.zip` (`LevelResource.MAP_RESOURCE_FILE`), not from
  `<world>/resources.zip` (1.21 and older). A `resources.zip` at the top of a 26.3 world does nothing: the file fix
  `ResourcePackLocationFileFix` moves it only when the client upgrades a world of an older version.
- `mc_shot.py --at Y` is the player position: the eye is 1.62 blocks higher. For a face at eye level of a unit on a
  block at y, use `--at X y+0.1 Z`.
- The same pack bytes on each system (#2741) need more than sorted names and a fixed time: the deflate of `zipfile`
  and of Pillow's PNG writer depends on the zlib of each build (Linux, Windows and macOS gave 3 SHA-1s), and
  `zipfile.ZipInfo` writes `create_system` 0 on Windows. Use `ZIP_STORED`, `stored_png()` and `create_system = 3`; the
  `bundles.yml` step "The world pack of the frozen command line is the release pack" checks it on each system.
