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
| Researched technologies | none | not parsed (the tech block of the player is skipped) |
| Game time | `match.duration` (0 for a header) | the game time of the save is in the header, not parsed |
| Map, terrain | `match.map.tiles`, `.dimension`, `.name` | read |
| Civilization, color, team | `Player.civilization`, `.color_id`, `.team_id` | read |

For hit points, resources, age and technologies the converter needs own code on the decompressed header
(`mgz.fast.header.decompress`), or a change of `mgz`.

## Open questions (only a real saved game answers them)

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
