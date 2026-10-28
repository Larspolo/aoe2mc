# World resource pack (`--resource-pack`)

The converter option `--resource-pack` (#2738, epic #2737) writes a resource pack into the world folder. Single
player loads it with the world. Without the option, the world is the same as before (`tools/world_diff.py`: "same").

## Layout

```
<world>/resourcepacks/resources.zip
    pack.mcmeta
    assets/minecraft/textures/entity/zombie/husk.png
    assets/minecraft/textures/entity/zombie/zombie.png
    assets/minecraft/textures/entity/zombie_villager/zombie_villager.png
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

## Client behavior (26.3, checked with `tools/mc_shot.py`)

- Single player (`--quickPlaySingleplayer`) loads the pack with no prompt: the log shows
  `Reloading ResourceManager: vanilla, vanilla, server/00000000/<uuid>` after the world loads.
- A pack that fails to load gives the prompt `multiplayer.texturePrompt.failure` (`WorldOpenFlows`).
- Multiplayer (`game/run.py`, #2740): `run.PackServer` serves the zip over HTTP on 127.0.0.1 (a free port), and
  `server.properties` gets `resource-pack`, `resource-pack-sha1`, `require-resource-pack=true` and
  `resource-pack-prompt` (`run.PROMPT`). Before the join the client shows "This server requires the use of a custom
  resource pack." with the prompt text and the buttons "Proceed" and "Disconnect". `mc_shot.Client` at 1280 × 720:
  click (407, 488) for "Proceed"; the player is in `list` only after it.

## Pitfalls

- 26.x reads the world pack from `<world>/resourcepacks/resources.zip` (`LevelResource.MAP_RESOURCE_FILE`), not from
  `<world>/resources.zip` (1.21 and older). A `resources.zip` at the top of a 26.3 world does nothing: the file fix
  `ResourcePackLocationFileFix` moves it only when the client upgrades a world of an older version.
- `mc_shot.py --at Y` is the player position: the eye is 1.62 blocks higher. For a face at eye level of a unit on a
  block at y, use `--at X y+0.1 Z`.
