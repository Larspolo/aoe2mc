# Music of the Minecraft client in the game program

Research for #5340 (part of #5337). Target: Minecraft Java 26.3. The game program wants its own peace and battle
music, with no music of the client over it.

## Result in short

- The client plays its own background music: a "music" event of the overworld dimension or of the biome
  (`music.game`, `music.creative`, `music.overworld.<biome>`). The next track starts at a random time
  **10 to 20 minutes** (12000 to 24000 ticks) after the end of the last one.
- `/stopsound @a music` stops the track that plays now. It does not turn the music of the client off: the client
  starts a new track 10 to 20 minutes later.
- A biome or dimension file can remove or replace the background music, but each `worldgen/` file makes the client
  show the "Experimental Settings" warning (`docs/datapack.md`). That breaks the default "worlds stay vanilla" mode.
- Use the music disc tracks (`music_disc.*`): each has one fixed length (`length_in_seconds`). The `music.*` events
  are pools of many tracks with different lengths, so the game program cannot know when one ends.

**Recommendation: stopsound only.** The game program runs `stopsound @a music` and then `playsound ... music @a`
for each new track of its own. It knows the end of its track by the length below and runs the pair again for the
next one. Because the client waits at least 10 minutes after a stop, and the program stops the music at each new
track (at most every 6 minutes, the longest track), a track of the client can only start in the short gap
between two own tracks, and the next stopsound ends it. It needs no datapack file and no warning. Biome music
(`--ambience full` only) is optional extra; it is not necessary.

## 1. `/stopsound @a music`

- `stopsound <targets> music` stops all sounds of the source `music` for the targets, also the background music of
  the client (`/stopsound`: https://minecraft.wiki/w/Commands/stopsound).
- The client music does not stop for good. The music manager sees that no track plays and sets the delay to the next
  track to a random value between `min_delay` and `max_delay` of the current music (12000 and 24000 ticks for the
  overworld, see section 2): 10 to 20 minutes ("Music", "randomly plays 10 to 20 minutes after currently playing
  tracks are finished": https://minecraft.wiki/w/Music).
- The player option "Music Frequency" (Music & Sounds) changes the delay (https://minecraft.wiki/w/Music). The
  game program cannot set it. Play the own tracks with the source `music` too, so that the "Music" volume slider
  of the player controls them.
- Not tested on a real client in this note (no client sound output in the cloud). The next sub-issues check it with
  `tools/mc_shot.py` logs.

## 2. Biome and dimension music

- 26.3 moves `effects.music` to the attribute `minecraft:audio/background_music` (`docs/datapack.md`, table "Map of
  the 1.21.1 effects fields"). Mojang data, `misode/mcmeta` branch `26.3-data`:
  - `data/minecraft/worldgen/biome/forest.json`: `"minecraft:audio/background_music": {"default": {"sound":
    "minecraft:music.overworld.forest", "min_delay": 12000, "max_delay": 24000}}`
    (https://github.com/misode/mcmeta/blob/26.3-data/data/minecraft/worldgen/biome/forest.json).
  - `data/minecraft/dimension_type/overworld.json`: `default` `music.game` and `creative` `music.creative`, both
    12000 to 24000 ticks (https://github.com/misode/mcmeta/blob/26.3-data/data/minecraft/dimension_type/overworld.json).
    A biome with no `background_music` uses the music of the dimension. So a biome alone cannot give "no music";
    the dimension type must change too.
- The old fields `replace_current_music` and the weighted music list ("Biome definition":
  https://minecraft.wiki/w/Biome_definition) let a biome stop the current track at once or select from own tracks.
  A custom track must be a sound event (a resource pack for a new one).
- Any file in `worldgen/` gives the "Worlds using Experimental Settings are not supported" warning
  (`docs/datapack.md`, tested in #218). A `dimension_type` override is a registry file too; expect the same warning
  (not tested). So biome music is only allowed with `--ambience full` (owner choice in #219), not in the default.

## 3. Track lengths

`length_in_seconds` of each jukebox song, `data/minecraft/jukebox_song/<name>.json` in `misode/mcmeta` `26.3-data`
(https://github.com/misode/mcmeta/tree/26.3-data/data/minecraft/jukebox_song). Sound event: `music_disc.<name>`.

| Track | s | Track | s | Track | s |
|---|---|---|---|---|---|
| 11 | 71 | creator_music_box | 73 | otherside | 195 |
| 13 | 178 | far | 174 | pigstep | 149 |
| 5 | 178 | lava_chicken | 134 | precipice | 299 |
| blocks | 345 | mall | 197 | relic | 218 |
| bounce | 234 | mellohi | 96 | stal | 150 |
| cat | 185 | | | strad | 188 |
| chirp | 185 | | | tears | 175 |
| creator | 176 | | | wait | 238 |
| | | | | ward | 251 |

The `music.*` events (`music.game`, `music.overworld.*`, ...) select a random track of a pool of tracks of
different lengths at each play (https://minecraft.wiki/w/Music, "Data values"). They have no fixed length: do not
use them for a playlist.

## 4. Candidate tracks

All pass `tools/mcvalid.sound_error` (26.3 sound list).

| Use | Sound event | s | Why |
|---|---|---|---|
| peace | `minecraft:music_disc.far` | 174 | slow, calm |
| peace | `minecraft:music_disc.mall` | 197 | calm, melodic |
| peace | `minecraft:music_disc.strad` | 188 | light, calm |
| peace | `minecraft:music_disc.wait` | 238 | slow, calm |
| battle | `minecraft:music_disc.pigstep` | 149 | fast beat, tense |
| battle | `minecraft:music_disc.otherside` | 195 | fast, driving |
| battle | `minecraft:music_disc.precipice` | 299 | tense, driving |

Command: `playsound minecraft:music_disc.far music @a ~ ~ ~ 1 1 1` (a minimum volume of 1 makes the player hear
it everywhere, https://minecraft.wiki/w/Commands/playsound). Put the names and lengths in a data file of the game
program (`docs/extend.md`), not in code.
