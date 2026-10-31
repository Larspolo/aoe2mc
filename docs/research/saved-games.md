# Saved games of AoE2 DE (#4562)

Research for epic #4561: how the converter can read a saved game (`.aoe2spgame`, `.aoe2mpgame`). Tested with
`mgz` 1.8.51 on 2026-10-30.

## File layout

A recorded game (`.aoe2record`) has this layout (`mgz.fast.header.decompress`, `mgz/__init__.py`):

| Bytes | Content |
|---|---|
| 0–3 | `header_length` (uint32): the length of the header block with this prefix |
| 4–7 | `next_chapter` (uint32; 0 in `samples/de-64.3.aoe2record`) |
| 8 – `header_length` | the header: a raw deflate stream (`zlib.decompress(..., wbits=-15)`) |
| next 4 | `log_version` (uint32) |
| then | the body: a meta block, then operations (sync, actions, chat, postgame) |

The header is a save of the game state at the start of the record. A saved game probably has the same header form
with no body (open question 1).

**A real DE save has no `header_length` prefix** (#4706, `samples/aoe2mc-sample.aoe2spgame`, DE for Mac 1.3, build
493785): the whole file is one raw deflate stream (7 156 774 bytes, `VER 9.4`, save version 68.9). `saved_match`
adds the prefix (`header_length`, a zero `next_chapter`) in memory. mgz 1.8.51 does not know the DE header of save
68.9: `aoe2mc.new_saves` adds the changes below (#3686, #5178).

## Field changes of save 68.9 (#5178)

Found by a compare of the save with `samples/de-regicide.aoe2record` (save 68.9, build 188329) and with the mgz
reads of save 66.6. Both 68.9 files have the same layout.

| Part | Change from save 66.6 | Read |
|---|---|---|
| DE header (`parse_de`) | one more DE string at the end of each player; two more DE strings after the string before the timestamp | `new_saves`, a patch of the mgz source (#3686) |
| Scenario: triggers | the trigger version is 5.0 (mgz looks for 4.5 or earlier): mgz then reads the triggers from a wrong place | not needed: `lobby_at_end` skips the part |
| Scenario: after the triggers | a new block of the XS state with no length field: 395 813 bytes in both files, with the string `Scenario Triggers` and the names of the XS runtime (`EXTERN$c...`, `xsGetUnitPosition` ...). A scenario with an XS script can change its length | skipped |
| Lobby (`parse_lobby`) | the same fields; 24 more bytes after the seed. It is the last block of the header | `lobby_at_end`: finds the lobby from the end by the map size of `parse_map`, and keeps the place only when the lobby ends 24 bytes before the end |
| Lobby chat | a save keeps the game messages of the player in it (`--Villager Created--`, `--Loom Research Complete--` ...): 16 in the sample | mgz `parse_chat` drops them |

Before #5178 the lobby of a 68.9 record read as zeros (population 0, no team lock, seed 0), and the save failed
with `unpack requires a buffer of 4 bytes` (the read went past the end of the header).

**The sample** (`aoe2mc-sample.aoe2spgame`, #5178): game time 9:03, Arabia, Tiny. Player 1 (`Player`, Huns) and
player 2 (`Samaratungga`, Malay, the AI) are both in the Dark Age: attribute 6 (current age) is 0, attribute 21
(technology count) is 1 for player 1, food is 313 (the Feudal Age costs 500), and the game messages name Loom but
not the Feudal Age. So the file has Loom only, not the Feudal Age and Double-Bit Axe of #4623.

## Read path

- `mgz.fast.header.parse(f)` reads the header. It needs the 4 bytes of `log_version` after the header block
  (`parse_version` reads them). A file of only `header_length` bytes fails: `could not parse: unpack requires a buffer
  of 4 bytes`.
- `mgz.model.parse_match(f)` (the path of `aoe2mc.read_record`) also reads the body meta block (`mgz.fast.meta`).
- **Test** (`samples/de-64.3.aoe2record`, header block cut to a temporary file):
  - Header only: `parse_match` fails, `could not parse: unpack requires a buffer of 4 bytes`.
  - Header + `log_version`: `parse` reads it (save version 64.3); `parse_match` fails, `insufficient meta received`.
  - Header + `log_version` + 40 zero bytes: `parse_match` reads it. Duration 0:00:00, 2 players, 15 objects of
    player 1, start position (37.0, 98.0), map "TTL4 Acropolis v3".
- **Wrapper**: when the file ends after the header, append the missing `log_version` and 40 zero bytes (an empty
  meta block) in memory (`io.BytesIO`), then call `parse_match`. The log version of a save is not known: use the
  value of a record of the same save version.

## Fields for the next tickets

| Need | `mgz` name | State |
|---|---|---|
| Objects of each player | `match.players[i].objects`, `match.gaia` | read |
| Object type | `Object.object_id`, `.class_id`, `.name` | read |
| Position | `Object.position.x`, `.position.y` | read |
| Owner | the player of the list (`Player.number`) | read |
| Object id | `Object.instance_id` | read |
| Hit points | none | `parse_object` skips it |
| Resources | none | `aoe2mc.saved_match` reads them before `parse_player` skips them (#4565): from save 63 each attribute has 8 bytes, the first half of the block is the floats (0 food, 1 wood, 2 stone, 3 gold) |
| Age | none | attribute 6, "current age" (0 = Dark Age), read with the resources (#4565) |
| Researched technologies | none | `aoe2mc.save_techs` (#4623): the tech table of the player, about 5 000 bytes after the attributes; see below |
| Game time | `match.duration` (0 for a header) | the game time of the save is in the header, not parsed |
| Map, terrain | `match.map.tiles`, `.dimension`, `.name` | read |
| Civilization, color, team | `Player.civilization`, `.color_id`, `.team_id` | read |

For hit points, resources, age and technologies the converter needs own code on the decompressed header
(`mgz.fast.header.decompress`), or a change of `mgz`.

## The tech table of a player (#4623)

Found by a diff of two saves of one game (`samples/aoe2mc-tech-a`, `-tech-b`: Loom only between them) and checked
with `samples/aoe2mc-sample-feudal.aoe2spgame` (Loom, the Feudal Age, Double-Bit Axe).

- A count (int32, 1510 in save 68.9), then one record per AoE2 tech ID, in ID order. A record has 76 to 102 bytes
  and the anchor `60 0a 00 00 60 0a 00 00 60 0a`. One record (after ID 1150) has no anchor: the gap is 162 bytes.
- 15 bytes before the anchor: the research time (float, seconds: Loom 25.0, the Feudal Age 130.0) and the state
  (int16: -1 not available, 0 not yet, 1 available, 3 done).
- A free technology of the civilization or the age has state 3 and time 0: it is not in "techs".
- Loom of save B also changes the unit tables of the player (villager hit points 25 → 40, armor): no tech data.

 (only a real saved game answers them)

1. Does a DE saved game start with `header_length` and a raw deflate block, as a record does?
2. Does it have bytes after the header (`log_version`, a meta block), or does the file end?
3. Is the save version of a save the same as the one of a record of the same game version?
4. Do the anchors of `mgz.fast.header` (the `Gaia` name, the object start pattern, `PLAYER_END`) also match in a
   save made late in a game, with many objects? `parse_player` already says: "this issue happens on restored games".
5. Where is the game time of the save in the header?

## A public sample

No public DE saved game with a license was found in this ticket (no web search done). Candidates to check: the
issues and test data of `happyleavesaoc/aoc-mgz` on GitHub, and the `aoe2.net` forums. Do not download from a host
that `scripts/allowed-domains.txt` blocks.
