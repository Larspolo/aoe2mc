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
- The zip has the same bytes for each conversion: sorted names and a fixed time (a release holds the same bytes).

## Client behavior (26.3, checked with `tools/mc_shot.py`)

- Single player (`--quickPlaySingleplayer`) loads the pack with no prompt: the log shows
  `Reloading ResourceManager: vanilla, vanilla, server/00000000/<uuid>` after the world loads.
- A pack that fails to load gives the prompt `multiplayer.texturePrompt.failure` (`WorldOpenFlows`).

## Pitfalls

- 26.x reads the world pack from `<world>/resourcepacks/resources.zip` (`LevelResource.MAP_RESOURCE_FILE`), not from
  `<world>/resources.zip` (1.21 and older). A `resources.zip` at the top of a 26.3 world does nothing: the file fix
  `ResourcePackLocationFileFix` moves it only when the client upgrades a world of an older version.
- `mc_shot.py --at Y` is the player position: the eye is 1.62 blocks higher. For a face at eye level of a unit on a
  block at y, use `--at X y+0.1 Z`.
