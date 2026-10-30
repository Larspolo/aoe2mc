# Research: play AoE2 in Minecraft

Ticket #32. The vision: "bots playing AoE2 inside of MC, and players being able to play AoE2 in MC".
This document compares the platforms, proposes the smallest playable milestone and the next steps,
and tells how the work connects to the converter. The owner decides before work starts.

## What the converter gives now

The converter writes a static world. Units are mobs with `NoAI`, buildings are blocks, and the footprints
are full of `barrier` blocks. Nothing moves and nothing has game rules. To play, the world needs:

1. Game state: resources per player, population, hit points, build and train queues.
2. Commands from the player: select units, give orders (move, gather, build, attack, train).
3. Unit behavior: path finding, gathering, building, combat.
4. A view: the player must see the stockpile, the selection and the orders.
5. Bots: a program that gives orders for the other players.

## Platforms

| Platform | What it can do | Limits | Install effort for players | Can the agent build and test it in the cloud? |
|---|---|---|---|---|
| Datapack (commands and functions) | Scoreboards for resources, `/trigger` and item use for input, `/tp` and `/summon` for units, text displays and bossbars for the view. | No general programming language. Path finding and AI with commands only are slow and hard to write. All logic runs in the server tick (50 ms). | Copy one folder into the world. Vanilla client. | Yes: the vanilla server (Mojang hosts) loads it, as in `tools/mc_check.py`. |
| Server plugin (Paper) | Full Java API: entities, path finding of mobs (`Mob#getPathfinder`), events for clicks, scoreboards, inventories as menus. | Needs a Paper server. Single-player worlds cannot use it. | The player joins a server. Vanilla client. | No: `papermc.io` and `repo.papermc.io` are blocked. |
| Mod (Fabric or Forge) | Everything, also a top-down RTS camera and box selection on the client. | Client and server need the same mod and loader version. Each Minecraft update needs a port. | Install a loader and the mod. | No: `fabricmc.net` hosts are blocked. |
| External program (Python) + vanilla server through RCON | The program keeps the game state, does path finding on the block grid that the converter already knows, and sends commands (`/tp`, `/data`, `/scoreboard`) through RCON. A small datapack shows the view and reads the input. | RCON is a text protocol: one command per action. Movement is a series of teleports. The program must run next to the server. | The player joins a server (or a LAN world with RCON). Vanilla client. | Yes: Python, vanilla server, RCON on localhost. |
| Bot clients (Mineflayer, Mindcraft) | A bot joins as a player and acts as a player (walks, breaks blocks). Mindcraft connects LLMs to Mineflayer bots. | One bot is one player, not an army. LLM calls take seconds: too slow for unit control in real time. | None for players; Node.js on the server side. | Partly (Node.js packages from npm). |

Performance: AoE2 has up to 8 players with a population of 200 each, plus animals. More than about a
thousand mobs with AI make a vanilla server slow, because each mob runs its own goals and path finding
each tick (estimate; the Paper guides tune `entity-activation-range` and spawn limits for this reason).
Units with `NoAI` that a controller moves cost much less. A controller must also limit the commands per tick.

## Similar projects

- **Reign of Nether** (Forge, 1.19.2 and 1.20.1): an RTS camera mode, box selection, orders, buildings and
  tech trees in Minecraft. The nearest project to AoE2 gameplay. It shows that a full RTS needs a client mod.
  Sources: [modpackindex](https://www.modpackindex.com/mod/117424/reign-of-nether-boobcat-edition),
  [Modrinth (Better Edition)](https://modrinth.com/mod/reign-of-nether-better-edition).
- **MineFortress** (Fabric): a top-down camera and a village of "pawns" that the player commands.
  Source: [GitHub](https://github.com/NobleSkye/minefortress), [feed-the-mods](https://www.feed-the-mods.com/minefortress-rts-mod/).
- **Villager Recruits** with an RTS map command addon (Forge): click-to-move, waypoints, attack orders,
  formations. Source: [Modrinth RTS collection](https://modrinth.com/collection/7kGUkjzl).
- **Mindcraft / MineCollab**: LLM agents control Mineflayer bots. The paper reports that the agents do
  worse when they must work together and give detailed plans. Sources:
  [arXiv 2504.17950](https://arxiv.org/abs/2504.17950), [NeurIPS 2025](https://neurips.cc/virtual/2025/137194).

## Proposal

Use an **external Python program with a vanilla server through RCON, plus a small datapack** for the first
milestones. Reasons:

- Players need no mods and no Paper server. The world stays a normal vanilla world.
- The program can reuse the converter: the same tile grid, the same object list, the same block columns.
  Path finding on the tile grid (as AoE2 does) is simple in Python with `numpy`.
- The agent can test all of it in the cloud: the vanilla server already runs in `tools/mc_check.py`.
- Bots are Python code in the same program. They read the game state directly. LLM bots can come later
  as a slow "strategy" layer above scripted bots, not as unit control.

Change to a Paper plugin or a mod later only if the RCON program is too slow or the player needs an RTS
camera. The game state and the rules can then move to Java with the same design.

**Owner decision (2026-10-26):** use Minecraft path finding. The game program changes to a Paper server with a small
plugin, so that units keep their AI and walk with `Mob#getPathfinder().moveTo(...)` (orders) and their own goals
(fights). The players already join the server of the game program, so no single-player world is lost. The
converted worlds stay vanilla. See CLAUDE.md, "Minecraft features first".

**Owner decision (2026-10-26): the interface for choices.** A building with several options (train a unit, research,
age up) and the build menu of a villager open a **chest menu of the Paper plugin** (an inventory with item icons and
the cost in the item text), not the vanilla `/dialog` window and not clickable chat. A right click with the command
stick on an own building opens its menu; a click on an option queues 1, a shift click queues 5, and the menu stays
open, so a player clicks again to queue more (no separate "x5" button). The build menu closes after the choice: the
next click is on the ground.
Epic #618.

**Owner decision (2026-10-26): the hints of the available actions** (#797). The game program shows the actions that
the player can do now (for example "Right click: walk · Sneak + right click: deselect" while units are selected) in the
**action bar**, the line above the hotbar where Minecraft shows "Press Shift to dismount". The action bar fades after
about 2 s, so the program sends the hint again while the state lasts. The boss bar stays for the selected unit (#659),
the sidebar for the numbers (#744). Epic #793, work: #798.

**Owner decision (2026-10-26): the size of the horses** (#1096). The converter gives each cavalry horse the attribute
`minecraft:scale` 0.7 (`units.mounted`), in each converted world and in the game. A horse of scale 1.0 is 1.4 blocks
wide: up a slope it stands 1 block above its path point, misses it and walks at 4.2 blocks per second. At scale 0.7 it
is less than 1 block wide and walks up at its flat speed (16.4 to 17.3 blocks per second). Not chosen: a scale only in
the game program (two sizes of one unit) and an own path follower (own logic in place of Minecraft path finding).
Work: #1022.

**Owner decision (2026-10-26): the stance of the selected units** (#1106). The stance (aggressive, defensive, stand
ground, no attack) has a **chest menu of the Paper plugin**, with the same behaviour as the build menu of a villager
(#621): a right click on a selected military unit opens a menu with four items (sword, shield, iron bars, white
banner), a click sets the stance of the selection, and the menu closes. The menu has room for more unit commands
later (formations, delete). Not chosen: a hotbar item that goes to the next stance, and a chat command. Epic #1103.

**Owner decision (2026-10-27): go to places** (#1828, option B). A "Go to" compass in hotbar slot 2 (key 3) opens a
**chest menu** with each own town center, each saved control group and the next idle villager (the AoE2 keys H, a
double press of a group number, and "."). A click puts the player above the place, facing it, and a click on a group
selects it too (`game/goto.py`, #1830). The F key stays free (no swap-hands use) until the owner decides on it. A click
on an attack alert line in the chat goes to its place with the same view (`Alerts.view`, #1816).

### Smallest playable milestone: "villagers gather wood"

1. The converter writes `aoe2mc.json` into the world folder: each object with its AoE2 ID, name, owner,
   tile position and the UUID of its entity.
   The "players" of a scenario also have the start "resources", the "pop_limit" and "computer" of the
   tab "Players" of the editor (#2539). Also the "name" (not the default "Player N") and "lock_civ" (#3295): a
   locked player keeps its scenario civilization against `--civ`.
2. The program starts the vanilla server with RCON, reads `aoe2mc.json` and gives each unit of player 1 a tag.
3. Input: the player holds a "command stick" (`carrot_on_a_stick`). A right click on a villager selects it
   (glowing). A right click on a tree sends the villager there. The datapack detects the click with the
   scoreboard criterion `minecraft.used:minecraft.carrot_on_a_stick`; the program reads the player position
   and view direction and finds the target block on the known grid.
4. The villager walks there (a series of small `/tp` steps along the path), "chops" (the tree loses a log
   after some seconds) and walks back to the town center or a lumber camp.
5. View: a sidebar scoreboard shows wood, food, gold and stone of player 1.

The milestone is done when a player can select a villager, send it to a tree, and see the wood count go up.

### Next steps after the milestone

1. All four resources (berries, farms, gold and stone mines) and drop sites.
2. Train villagers at the town center (cost, queue, population limit with houses).
3. Build a building: place the design of `buildings.py` step by step as a construction site.
   The designs can be exported as structure templates (`.nbt`) or placed by the program.
4. Military units and combat: hit points, attack, range, the counters of AoE2.
5. A scripted bot for player 2 (gather, build, train, attack), then several bots.
6. Fog of war and line of sight (optional; hard in vanilla).
7. Measure: commands per second through RCON, server tick time with 200, 500 and 1000 units.

The owner chose the order in #357: A (item 1) #388, C (item 3) #394, D (item 4) #395, B (item 2) #396,
E (item 5) #397, F (item 7) #398. Each epic gets its sub-issues when the epic before it is done.
Item 6 (fog of war) has no ticket.

Selection of many units (#742): the owner chose in #745 a selection wand with two corners for the AoE2 selection box
(option A, #778: `Gather.box`, item `warped_fungus_on_a_stick` with its own "used" statistic `aoe_box`), and hotbar
items for the control groups later (option C, #779). A radius selection (option B) was not chosen.
On Paper the owner replaced the wand with the command stick (#1786, demo feedback): hold right click with the stick
to draw the box (`Gather.hold`, then the drag of #992), release to select. The first use of a hold is also a click, so a
stick use waits `HOLD` (0.2 s, the use period of a held button): a next use in that time makes a hold, else
`Gather.short` runs the click with the look of the use. A short click is one loop call (`tick` 0.25 s) later than before.
No pending use while a foundation or a rally point waits. Vanilla keeps the wand and its two clicks.
Control groups (#779, `Gather.group`): carrots on a stick "Group 1" to "Group 5" in hotbar slots 5 to 9
(`custom_data` `{aoe_group:N}`). A shift right click (vanilla predicate `is_sneaking`) saves the selection as group N,
a right click selects the live units of group N. The click item is `carrot_on_a_stick[!custom_data]`.

## Measured gather timing (#289)

`python3 tools/measure_gather.py` plays a fixed map on a real server without a client: one villager of player 1,
a town center and one tree in one row, 10 tiles from the center of the town center. It sends the villager to the
tree (no click), plays until 2 loads are at the town center, and reads the event log of `game/gather.py`
(`Gather(log=...)`, also `game/run.py --play --log FILE`; `--read FILE` reads a log of a real game).
Result (Minecraft 26.3 server in the cloud, `--tile-size` 4, `gather.py` defaults `tick` 0.25 s, `chop` 1.0 s, `carry` 10):

| | measured | configured | AoE2, per game second | AoE2 at Normal speed (1.7×) |
|---|---|---|---|---|
| Walk (blocks/s) | 3.93 | 4.00 | 3.20 | 5.44 |
| Chop (wood/s) | 0.99 | 1.00 | 0.39 | 0.66 |
| One trip of 62 blocks (s) | 26.0 | 26.0 | 45.0 | 26.5 |

- AoE2 values: AoE2 DE `empires2_x2_p1.dat`, unit 123 `VMLUM` (lumberjack): `speed` 0.8 tiles/s, `work_rate`
  0.39 wood/s, `resource_capacity` 10, per game second (owner's data in #267). Normal speed is 1.7× real time.
- The server keeps the tick: the measured values are within 2 % of the configured values. The `mc` test
  `test_measured_gather_timing_is_near_the_configured_timing` fails above 10 %.
- Compared with AoE2 at Normal speed, the villager walks 26 % slower and chops 1.5× faster. For this
  distance the two errors cancel: one trip takes about the same time as in AoE2.
- A diagonal step is 1.41 blocks in one tick, so on a diagonal path the villager walks 41 % faster.
- Each state change costs one tick (0.25 s), and a walk of n blocks takes n ticks.

Per resource (#393): `python3 tools/measure_gather.py --resource {wood,food,farm,gold,stone}` puts a tree, a fruit
bush, a farm, a gold mine or a stone mine at the same place. Since #413 each resource has its AoE2 work rate at
Normal speed (`gather.WORK_SECONDS` = 1 / (`AOE2_WORK` × 1.7) seconds per unit; the table above is from before, with
`chop` 1.0 s for all). Work rates in resource/s, trips in s (the farm trip is shorter: the farmer stands on the farm):

| Resource | work measured | work configured | AoE2 work, per game second | AoE2 work at Normal speed | trip measured | trip configured | AoE2 trip at Normal speed |
|---|---|---|---|---|---|---|---|
| Wood (tree) | 0.65 | 0.66 | 0.39 | 0.66 | 31.3 (62 blocks) | 31.1 | 26.5 |
| Food (fruit bush) | 0.53 | 0.53 | 0.31 | 0.53 | 35.0 (62 blocks) | 35.0 | 30.4 |
| Food (farm) | 0.55 | 0.56 | 0.33 | 0.56 | 32.5 (56 blocks) | 32.3 | 28.1 |
| Gold (mine) | 0.64 | 0.65 | 0.38 | 0.65 | 31.5 (62 blocks) | 31.5 | 26.9 |
| Stone (mine) | 0.60 | 0.61 | 0.36 | 0.61 | 32.6 (62 blocks) | 32.3 | 27.7 |

- The walk speed is 3.92 to 3.93 blocks/s for all resources (configured 4.00).
- AoE2 work rates (`gather.AOE2_WORK`): lumberjack 0.39 from #267 (`empires2_x2_p1.dat`); forager 0.31, farmer 0.33,
  gold miner 0.38 and stone miner 0.36 are the published AoE2 DE gather rates, not read from the `.dat` file here
  (the file is not in the cloud environment).
- The `mc` tests `test_measured_gather_timing_is_near_the_configured_timing` (wood) and
  `test_measured_rates_per_resource` (`tests/test_measure_gather.py`) fail above 10 %.
- The work rates are now within 2 % of AoE2 at Normal speed. The villager walks 26 % slower than in AoE2, so the
  trips of this distance take 15 % to 18 % longer.

## Measured unit count (#398)

`python3 tools/measure_units.py` (#943) on the cloud machine (4 cores, 15 GB, Paper 26.3, no client, the `battle`
scenario with its 170 units that stand still): husks (the mob of most units) on free cells near the map center, each
with its own `aoe moveto` to a cell up to 12 blocks away every 5 s (2 RCON commands: the walk speed and the order).
All orders reached their unit. 2026-10-26:

| Units | Commands per second | Mean tick ms | P99 tick ms | Ticks per second |
|---|---|---|---|---|
| 200 | 1314 | 7.35 | 48.3 | 20.0 |
| 500 | 2134 | 12.40 | 37.5 | 20.0 |
| 1000 | 1346 – 1896 | 24.35 – 25.35 | 52.7 – 109.2 | 20.0 |
| 1500 | 817 | 37.60 | 74.2 | 20.0 |
| 2000 | 317 | 45.30 | 74.2 | 20.0 |
| 3000 | 19 | 56.70 | 108.1 | 17.6 |

Without `datapacks/aoe2mc`: 200 units 6.95 ms, 500 units 12.20 ms, 1000 units 23.95 ms: the datapack costs less
than 1 ms per tick.

- **Largest count at 20 ticks per second: 2000 units** (mean 45 ms of the 50 ms of a tick). The tick time grows by
  about 0.024 ms per walking unit: the entity ticks and the Minecraft path finding of the mobs.
- **Largest count that gets its orders in time: about 1500.** RCON commands run on the main thread between the
  ticks, so the command rate falls when the ticks get long. 1500 units need 600 commands per second for an order
  every 5 s and get 817; 2000 units need 800 and get 317, so a round of orders takes 13 s.
- AoE2 has at most 200 units per player (8 players: 1600). The game program keeps 20 ticks per second with that
  count; with more than about 1500 units that get orders often, send the orders of a group in one plugin command.

### Cost of the fog of war (#1473)

`python3 tools/measure_units.py --units 200 --reveal all` and `--reveal normal` (#1389), the same machine and scenario,
two runs of each, 2026-10-27. With `normal`, 100 units are own soldiers and 100 are enemies, and `fog.tick` hides the
enemies out of sight once per second. "Fog ms" is the mean time of one `fog.tick` in the game program: the
`aoe where` query of the positions (RCON), `Gather.seen_tiles` and the `aoe hide`/`aoe show` commands.

| Reveal | Run | Commands per second | Mean tick ms | P99 tick ms | Ticks per second | Fog ms |
|---|---|---|---|---|---|---|
| all | 1 | 2315 | 5.70 | 40.9 | 20.0 | – |
| all | 2 | 2053 | 5.75 | 51.0 | 20.0 | – |
| normal | 1 | 2222 | 5.30 | 48.1 | 20.0 | 36.4 |
| normal | 2 | 2375 | 5.85 | 61.7 | 20.0 | 25.1 |

- **The fog costs no measurable server tick time**: the mean tick is 5.58 ms with the fog and 5.73 ms without it
  (−2.6 %, inside the noise of two runs: 5.30 to 5.85 ms). The P99 tick time changes as much between two runs of one
  setting. The ticket limit (5 %) holds, so no change of `fog.py`.
- The game program spends 25 to 36 ms per second on `fog.tick` (2.5 % to 3.6 % of its time), with the RCON round
  trips. It runs between the orders and does not slow the order rate (2222 and 2375 commands per second).

## Connection to the converter

- The converted world is the start map. The converter stays the first step and needs only one change:
  write `aoe2mc.json` with the objects and the entity UUIDs (follow-up ticket).
- The converter puts `barrier` blocks in footprints. A game needs walkable doors and destroyable buildings,
  so the game program must know the footprint of each building (also in `aoe2mc.json`).
- Units with `NoAI` stay `NoAI`: the program moves them. This keeps the server fast.
- The game program goes in a new folder (for example `game/`), not in `aoe2mc.py`.

## Follow-up tickets

The owner decides on the platform first (decision ticket). The other tickets depend on it.

- #135 Choose the platform for gameplay in Minecraft (`needs-human`).
- #136 Write `aoe2mc.json` with the objects of the world.
- #137 Start a game program that controls the server through RCON.
- #138 Let villagers gather wood on the player's command (the milestone).

## Delete (#3452)

- AoE2 DE: the Delete button (bottom right of the command panel) makes an own building fall at once, as at 0 hit
  points: the units inside come out, the queue gives its cost back. `game/demolish.py` puts it in the last menu slot.
- A foundation that no villager started to build gives back its full cost; a started one gives back nothing.
  Source: the behavior of the game (AoE2 DE). The AoE2 wiki (MediaWiki API, 2026-10-29) has no page "Delete" and no
  refund rule on "Building (Age of Empires II)": check it in the game when a refund looks wrong.

## Unique buildings (#4081)

Source: the AoE2 wiki, category "Unique buildings (Age of Empires II)", the page "Unique building" and the infobox of
each page (MediaWiki API, 2026-10-29). Since update 141935 the wiki counts six. The shared buildings of The Mountain
Royals (Fortified Church, Mule Cart) are regional buildings now, not in this list. State: "works" when
`game/data/build.jsonl` has a line with the name.

| Building | Civilizations | Age | Cost | What it does in AoE2 | State |
|---|---|---|---|---|---|
| Donjon | Sicilians | Dark | 50 wood, 175 stone | Replaces the Watch Tower line; trains Serjeants and the Spearman line; upgrades free with each age | works |
| Feitoria | Portuguese | Imperial | 350 gold, 300 stone | Generates 96 food, 42 wood, 60 gold, 18 stone per minute; uses 20 population | missing |
| Folwark | Poles | Dark | 100 wood | Replaces the Mill; collects 10 % of the food of a nearby Farm when it is seeded; 5 population | works |
| Harbor | Malay | Castle (Thalassocracy) | 150 wood | Upgraded Dock: trains and improves ships, shoots arrows, garrisons 10 | missing |
| Krepost | Bulgarians | Castle | 350 stone | Small Castle: trains and upgrades Konniks, shoots arrows, 20 population | works |
| Pasture | Khitans | Dark | 110 wood | Replaces the Farm; two villagers work it at once; its own drop site | missing |

## Attack Ground (#4078)

The AoE2 wiki ("Attack ground", the MediaWiki API) lists the AoE2 units that can attack a point on the ground:

- Mangonel → Onager → Siege Onager
- Rocket Cart → Heavy Rocket Cart
- Bombard Cannon → Houfnice
- Trebuchet, Mounted Trebuchet, Traction Trebuchet
- Cannon Galleon → Elite Cannon Galleon
- Dromon, Lou Chuan, Turtle Ship → Elite Turtle Ship

Only the shots with an area damage hit at the point: a Turtle Ship fires its cannonballs and rockets, a Lou Chuan only its rocks.
The plugin command `aoe attackground <selector> <x> <y> <z>` takes each unit with a siege shot (`aoe range` with a blast).
A unit with blast 0 (the Trebuchet) shoots, but its shot hits no unit at the point.

## Civilization choices (#4747)

The lobby options of AoE2 DE for the civilization of a player (part of epic #4745). The cloud blocks the wiki hosts
(HTTP 403): the rules come from the game and the wiki pages below; a later run with access checks the links.

| Option | Rule in AoE2 DE | Source |
|---|---|---|
| Per-player civilization | Each player selects one civilization in the lobby. | [Civilizations](https://ageofempires.fandom.com/wiki/Civilizations_(Age_of_Empires_II)) |
| Random | The game gives the player one civilization from all civilizations of the game at the start. Players can get the same one. | [Game settings](https://ageofempires.fandom.com/wiki/Game_settings) |
| Random pool | The host disables civilizations; Random selects only from the enabled civilizations. | [Game settings](https://ageofempires.fandom.com/wiki/Game_settings) |
| Mirror | All players get the same civilization: the host civilization, or one random civilization for all when the host has Random. | [Game settings](https://ageofempires.fandom.com/wiki/Game_settings) |
| Team Random (same per team) | Each team gets one random civilization for all its players. | [Game settings](https://ageofempires.fandom.com/wiki/Game_settings) |
| Hidden civilizations | The lobby and the game show "?" for the civilization of the other players. The civilization shows in the end screen (Achievements). Allies see each other: the team bonus shows. | [Game settings](https://ageofempires.fandom.com/wiki/Game_settings) |
| Lock civilizations | A scenario keeps its civilizations; the lobby cannot change them. The converter keeps it: `lock_civ` (#3295). | `game/run.py` `apply_civs` |

The displays of the civilization of a player in the game program:

| File | Function | What it shows |
|---|---|---|
| `game/lobby.py` | `name` | The lobby menu: "Player N (Civ)", also "You play ..." and "... is taken" |
| `game/diplomacy.py` | `name` | The diplomacy menu: "Name (Civ)" of each player |
| `game/scenario.py` | trigger display (`trigger_civs`) | A scenario trigger renames the civilization of a player (#2905); lobby and diplomacy show it |
| `game/recap.py` | `give` (page lines) | The end book: "Player N (Civ)"; `RANDOM` shows no name |
| `game/replay.py` | `Replay.player` | The replay panel: "Name (Civ)" of the record |
| `game/techtree.py` | `view` | The tech tree: the own civilization first, the next and previous of all civilizations |
| `game/run.py` | `civ_choices`, `apply_civs` | The `--civ PLAYER=CIV` option; no Random, pool, Mirror or Hidden value yet |

The score panel (`game/score.py`), the tab list and the chat show no civilization. Hidden civilizations must change
`lobby.name`, `diplomacy.name` and `techtree` (it lets a player open any tree, which is no leak), and keep `recap` (the
end screen shows all).

Tickets for the refill (items 3 and 4 of #4745): Random #4755, Random pool #4756, Mirror and Team Random #4757,
Hidden civilizations #4758. The "?" text against no civilization text for hidden players is the
decision ticket #4754.

## Decisions of the owner (2026-10-28)

- Bot difficulty (#2648, option A): the six AoE2 DE names (Easiest, Standard, Moderate, Hard, Hardest, Extreme), each
  with its gather rate, first attack time and soldier count in a data file. AoE2 does not publish these values, so they
  are a guess that the owner can tune (#2661).
- Click on the minimap (#2585, option A): a map in an item frame (a "map table") near the own town center. A right
  click with the selection wand on a pixel of the framed map sends the selection there (#2586).
- Resources left (#3275, option B, #3284): a `text_display` above each partially drained tree, fruit bush, mine, farm
  and carcass shows the whole amount left (`game/amounts.py`). A full resource shows nothing; a carcass shows from the
  kill, because it rots at once.
- Co-op (#3488, option B, #3489): `game/run.py --play --seats 1,1,2` gives the AoE2 player of each person in join
  order. Two people on one player share its stock, population, units and score (one Gather), each with an own
  selection (#3486). The lobby menu still refuses a taken player.

## Pitfalls of the game program

Moved from `docs/LEARNINGS.md` (improve run, 2026-10-26).

- Paper: the jar host `fill-data.papermc.io` was blocked on 2026-10-26 (#439): test a download host with `curl`. The Paper
  API answers 403 to the `Python-urllib` User-Agent: send one (`game/run.py` `AGENT`). `-DbundlerRepoDir=DIR` keeps the
  patched Mojang jar; Paper writes `usercache.json` next to the `--universe` world (#434).
- Paper plugin (#435): `game/run.py` builds `game/plugin` with `./gradlew --no-daemon -q jar` and `JAVA_HOME` = JDK 25
  (`openjdk-25-jdk-headless`; javac 21 cannot read the paper-api 26.3 classes); first build 30 s. A NoAI mob finds no
  path before its first AI tick; a path ends at about `follow_range` (cow: 16); the world border stops paths.
- `build.place` draws the design with `replay.Replay.building`: fake `aoe2mc.json` data in tests needs `level_height`
  and a tile size of 4 (at tile size 1 most designs give no blocks). The site keeps the commands, bottom up (#418).
- Import cycle `gather` → `build` → `replay`: `replay` imports `gather` inside a function (#408). `gather` imports `build`
  and `train` at the top, and `combat`, `ai`, `replay` import `gather`: a module that `gather` imports must import `combat`
  or `gather` inside its function (#612).
- `gather.Map.path` on a whole record map (480 × 480): A* with a cell limit, about 45 ms per path, 0.3 s across the
  map. Replay paths cost 18 s per 200 s of game in samples/ (one search per unit of a group, #409).
- Paper 26.3 (#436): remove mob goals by `GoalKey` (`MobGoals.removeGoal(mob, key)`), on each order: removal by the
  goal object, and a removal only after `setAI(true)`, missed goals. `Zombie#setShouldBurnInDay(false)` does nothing:
  set the attribute `burning_time` to 0. `aoe goals <selector>` lists the goal keys of a unit.
- Mob walk speed on a path: blocks per second = 43.4 * `movement_speed` ** 2 (zombie, cow, horse, and villager: 42 to 44
  at 0.15 to 0.6 on stone bricks, #437; the "4 times slower" of #436 did not repeat). Villagers have a brain, not
  goals: the MobGoals API does not stop them. After an order they walk to each other: the plugin sets NoAI at the goal (#438), `aoe stop` too.
- `aoe moveto` of many units in a live replay (#438): an arrived villager strolls away (its brain), so the plugin sets
  NoAI on it at the goal; a goal more than about 100 blocks away gets no path (follow range 128): the replay sends
  legs of `replay.LEG` path cells. Check walks on a real server with `data get entity <uuid> Pos` after the replay.
- Paper (Spigot) entity activation range: without a player near, a unit ticks only now and then. A villager then does
  not walk or fall after `aoe moveto`, at random (#437: a farmer at the far end of its farm). `run.Game` writes a
  `spigot.yml` with all ranges 0 (always active, as in vanilla).
- A Paper `Goal` (MobGoals API) gets `tick()` only on each 2nd server tick: time a cooldown with
  `Bukkit.getCurrentTick()`, not with a counter in `tick()` (#515: the archer shot each 2.4 s, not 1.2 s).
- A vanilla melee goal hits only a target in sight of its eye (#517): the stand-in slime of a building has its eye in
  the walls, so the zombie walks to the wall and never hits. The plugin hits for it (`siege()`, `Mob#attack`).
  Debug an attack on a server with `data get entity <uuid> Pos` and `aoe goals` once per second.
- The server cannot open an inventory without a joined player (#619): an `mc` test of a chest menu checks only the
  command answers ("Menu: 0 players", "Bad item"). Real clicks need a client on the server (#627).
  `scoreboard objectives list` shows the display names (`[Menu]`), not the objective names.
- After `/kill <UUID>` the server still finds the entity by its UUID for 20 ticks (the death animation): `execute if entity <UUID>` gives "Test passed" at once. Poll for about 2 s in a test (#630).
- A real client joins the Paper server of `run.Game` (`online-mode=false`) with `--quickPlayMultiplayer 127.0.0.1:PORT`
  (`mc_shot.Client`, #627). In an open inventory the pointer is free: `xdotool mousemove` + `click` hits the slots.
  A Paper display name of an item is italic by default (Adventure).
- A building target (#660): `damage <uuid> 1 ... by <mob>` answers "Target is invulnerable" and the plugin counts no hit
  (most runs): hit it with `aoe attack`. `execute if entity <uuid>[tag=T]` is not valid syntax and never passes:
  use `@e[type=slime,tag=T]`. A NoAI zombie burns in the sun at y 200: use a `husk`.
- `summon skeleton` with NBT gets no bow: `RangedEntity#rangedAttack` then throws "Invalid weapon firing an arrow"
  and the server removes the mob ("No entity was found" right after the order). Give
  `equipment:{mainhand:{id:"minecraft:bow",count:1}}`. A Java exception of the plugin is only in `game.server.log` (#608).
- An arrow at the stand-in slime of a building sticks in the walls first (#608): the range goal counts each shot itself.
- One hit of a unit in an `-m mc` test, without a chase: `damage <victim> 1 minecraft:mob_attack by <attacker>` fires `EntityDamageByEntityEvent`, so the plugin takes the AoE2 damage of the attacker (#733). Since #733 a hit unit without an order hits back: a test of one-sided damage gives the target an order or no AoE2 values.
- A horse has no attack goal, and `aoe attack` on it does nothing. Give the target to the rider: a riding mob walks with the navigation of its vehicle (vanilla `Mob#getNavigation`), so the horse follows, and its follow range limits the path search (#710).
- A cancelled `EntityDamageByEntityEvent` of an arrow lets the arrow fly on, and it can hit the next entity on its way (a moving horse under the hit rider: two hits in one tick, #733). Remove the projectile after the hit.
- A RCON command of more than 1446 bytes: the server closes the connection ("the server closed the RCON connection"). Keep long `tellraw` texts short (`separators=(",", ":")`, style of the parent in `extra`) and test the length (#688).
- A `block_display` takes the light of the block at its position: a ghost whose anchor is inside a slope draws black. Set `Display.Brightness(15, 15)` (#794). A `tp` of a creative player in the air lets it fall before a screenshot: use spectator mode.
- On Paper, a unit of `aoe moveto` walks slower than `ai.WALK` on slopes and around trees (villager 9935 of `de-64.3`: about 5.6 instead of 12.8 blocks per second at speed 4): the replay position is ahead of the entity. `Replay.arrived` reads it before the first gather step (#766).
- The `uuid` of a mounted unit or a ship in `aoe2mc.json` is its vehicle (horse, ravager, boat): it has no team and no `aoe2mc.pN` tag, so `kill @e[tag=aoe2mc.pN]` leaves it. Kill it first: `execute as @e[tag=aoe2mc.pN] on vehicle run kill @s` (#819). A killed mob stays 20 ticks: `execute if entity` passes for 1 s.
- A mob jumps at each step of one block (attribute `step_height` 0.6) and loses speed in the air: on the bumpy ground of a converted map the replay villagers walked at 64 % of their speed. The plugin sets `step_height` 1 on each order (#829). Measure a walk speed with `tools/replay_drift.py --every 2`: with 10 s between samples a detour looks like a slow walk (82 % instead of 91 %).
- A wait loop with a fake clock (`now += s`) runs forever when the wait is about 1e-15: `now + 1e-15 == now`. Break on `wait <= 1e-6`, not `<= 0` (#685).
- Screenshots of a game check: join `mc_shot.Client(game.game_port, game.version)` to the running `run.Game`, `gamemode spectator aoe2mc`, then `tp aoe2mc X Y Z facing entity <uuid>` and `client.shot()`: no saved world, no copy of the `.dat` files. The server log is `game.folder/logs/latest.log`: read it before the `with` ends (#603).
- `run.Game(world)` plays on the world folder itself (`--universe`, no copy): the game saves its changes there. Copy the converted world for each check run, else the second run starts with felled trees and empty bushes (#718). A live replay at `--speed 8` leaves the real villagers far behind the replay positions: check at speed 4.
- `mc_shot.Client` hides the chat (`chatScale` 0): pass `chat=True` for an image of a message. The client log (`client.text()`, `[CHAT]`) has each chat line; the server log has no `tellraw` text. `Gather.setup` reads no stock from the sidebar: set `scoreboard players set Food aoe_res N` with `g.stock` (#780).
- `execute if entity @e[...]` on 26.3 answers "Test passed. Count: N" (a capital C, a full stop); the `FakeServer` of `tests/test_gather.py` writes "Test passed, count: 1". Match `Count: (\d+)` and check a new answer on a real server (#787).
- A fruit bush of `place_objects` is at block `int(x * T)` (the tile center), not at `int(tile) * T` (#391).
- `game/build.py` has a function `menu()` (the chat text of /trigger): it imports `game/menu.py` as `chest` (#621).
- A train test (`game/train.py`) needs an own `TOWN_CENTER` or `HOUSE`: without them the population limit is 0 and `tick()` spawns nothing (#654).
- `game/combat.py` `stats()`: a name that is not a `STATS` key gets `DEFAULT` (40 hit points) without a warning. The units of `aoe2mc.json` have names like `VILLAGER_MALE`: compare with `units.classify` names, not the table keys (#655).
- A new item of a building menu (`train.show()`): the menu tests build the expected text from the data (`item()` of `tests/menu_line.py`, `entry()` of `tests/test_castle_upgrades.py`). Do not add a literal menu string with a cost or a slot (owner, 2026-10-29).
- `game/replay.py` uses the resource looks of `gather.Gather` through `Replay.crew` (`Gather.__new__` with `map`, `trunks`, `bushes` and a `command` attribute): no copy of the look code (#631).
- `test_gather_attack.click` puts the eye at the ground height (y 64): its ray cannot hit the ground, so `pick_ground` and `build.pick` give the wrong cell. For a ground click put the eye 2 blocks up (`tests/test_order_marker.py` `look`, #796).
- `Replay.run` gives `control["time"]` as a float (ms): a test of a poll action with an int time hides a format error like `:02d` (#803). Test with a float time, or with `Replay.run` and the `Clock` fake of `tests/test_replay_control.py`.
- `Gather.__new__` adapters (`tests/test_menu.py`, `Replay.crew`) have no attribute of `Gather.__init__`: a new attribute that `clicks()` or `setup()` reads also needs a class default (`cheats = False`, #816).
- `Replay.run(..., bar=False)` sends no `tag ... add aoe2mc.pop` for the start units (the `send` of the bar): a tool that selects `@e[tag=aoe2mc.pop]` must pass `bar=True`, as `run.py --replay`. `v.pos` of a walking unit is the end of its leg, not the place where it is due now (#813).
- `tests/test_menu.py` `test_gather_reads_the_menu_clicks` makes a `Gather.__new__` with only the attributes of `clicks()`: a new attribute that `clicks()` reads (`calls`, #779) needs a line there too.
- A minecart that rides a mob pushes that mob: the carrier pig of a siege unit creeps on at about 0.5 blocks per second after its walk. `follow()` turns its AI off on arrival, as for villagers (#836). Vanilla `attribute` fails on a minecart: `ai.speed_command` sends `aoe speed` for `units.siege` names.
- A moss carpet or `snow[layers=2]` on a ground step makes it 1.06 or 1.25 blocks high: at `step_height` 1 a husk stood still in front of it for 10 s, so the plugin sets 1.25 (#851). Down a slope a mob walks at most about 5.7 blocks per second, whatever its speed (#888). Find such a cause with one unit on the real world: summon it, `aoe moveto`, read `Pos` every 0.25 s.
- `~` in an RCON command is relative to the world spawn, not to the target entity: keep the y of a boat with `execute as U at @s run tp @s X ~ Z` (`replay.sail`, #866). A `/tp` of a boat keeps its crew. `data get entity BOAT Passengers` shows the crew NBT without its `id`: test the crew with `execute as @e[tag=T] on vehicle`.
- A replay unit of the plugin stands up to `replay.NEAR` blocks from `v.pos`: a command aimed from `v.pos` (the point of the tree next to it) can be 40° off for the entity. Aim at the middle of the target, and read `Rotation` and `Pos` of the entity in a Paper check (#867).
- A slow walk of a replay unit in `tools/replay_drift.py`: first print the ground height along its way (`gather.Map.y`). The "town" of player 1 of `samples/de-64.3.aoe2record` (x 110 to 175, z 327 to 353) is a slope of 1 block per block, so its slow horse was the descent of #888, not the width of the horse (#889). One horse on flat ground walks at its full speed (4.81 of 4.8 blocks per second).
- `tp PLAYER X Y Z facing X Y Z` aims from the feet, not from the eyes: `Gather.click` then picks nothing. For a click check compute the yaw and the pitch from the eye (y + 1.62) yourself (#823, script on `checks/823`).
- `test_gather_attack.click` puts the eye at the ground height (y 64): its ray cannot hit the ground, so `pick_ground` and `build.pick` give the wrong cell. For a ground click put the eye 2 blocks up (`tests/test_order_marker.py` `look`, #796).
- `Replay.run` gives `control["time"]` as a float (ms): a test of a poll action with an int time hides a format error like `:02d` (#803). Test with a float time, or with `Replay.run` and the `Clock` fake of `tests/test_replay_control.py`.
- `FakeServer` of `tests/test_gather.py` moves an entity only on `tp U X Y Z <more>` (a `tp` without `facing` keeps its Pos): check the `tp` text in `server.log`. A fake answer for `execute if entity X` must skip `@a[scores=...]`: `Gather.clicks` asks that (#808).
- Two equal melee units in a duel: the result depends on the tick of the first hit. A defender that hits back in the same tick ties (both die); `attackBack` gives it half a reload of reaction (#848).
- A screenshot of an order marker in Xvfb: dust and the glowing effect last about 1 second, and the software renderer
  draws few frames, so one `client.shot` after the commands shows nothing. Send the marker commands again each 0.2 s
  in a thread and take the shot after about 1.5 s (#845). The plugin sets the AoE2 hit points itself: `effect give
  resistance` does not keep an attacked unit alive for the shot, so put the attacker far from the target.
- A test server with no player: an entity that RCON summons in an unloaded chunk is gone at once ("Summoned", then `data get` finds nothing). `forceload add` the area first, wait 2 s, and `kill` the older entities of the type before `@e[...,limit=1]` (#844).
- `Pathfinder.moveTo` to the same target keeps the old path (Minecraft `createPath` returns the current path for the same target): call `stopPathfinding()` first to get a new path from the place of the mob (#888). So the `moveTo` of `follow()` every 2 ticks does not search again while the path is not done.
- A mob has almost no control in the air (0.02 blocks per tick, drag 0.91): down a 1:1 slope a fast unit is in the air most of the time and flew at about 5 blocks per second for each `movement_speed`. The plugin `glide()` keeps its walk speed in the air (#888). To measure a walk, read `Pos`, `Motion` and `OnGround` with one `data get entity ... KEY` each: the whole entity NBT is too long for one RCON answer.
- A `text_display` with scale 1 is a few pixels high from 35 blocks (1280 × 720): give a text that a spectator must read from far a `transformation` with `scale:[4f,4f,4f]` (all four keys of `transformation`, #843).
- `run.Game(world)` runs the server on the world folder itself and saves into it: units that died or walked stay so in the next run. Copy the world (`shutil.copytree`) before each check run, else a second run finds dead units (#934).
- `tests/test_replay_control.py` `Clock` and the client test of `tests/test_replay_input.py` take each `tellraw @a` as a chat event of the timeline (a list with a `t<N>` text): a new `tellraw @a` of `Replay.run` (the view text of #737) broke them. Mark the event texts, or match only `tellraw @a [` (#737, #910).
- A converted unit has no team until the datapack pulse reaches its loaded chunk: take the side of a unit from its team, else from its tag `aoe2mc.pN` (`AoePlugin.side`). Two units without a team are not allies to `getEntityTeam`, so idle soldiers killed their neighbours at the start (#986).
- A `moss_carpet` is 1/16 block high: under leaves 2 blocks above the ground a unit of 1.95 blocks does not fit on it, and Minecraft finds no path through the cell (the eagle scout of `de-64.3` stood still for 40 s at a forest). `build_chunk` removes such ground carpets (#889). Find such a cell with one unit: `tp`, `aoe moveto`, then `setblock` the suspect block to air and try again.
- The path points of a mob wider than 1 block (a horse: 2 × 2 blocks) have their center at the corner + 1.0, not + 0.5 (vanilla `Path#getEntityPosAtNode`): the plugin `center()` (#889). A glide toward a point closer than one tick of travel overshoots it and turns back each tick.
- `tools/replay_drift.py --speed 4`: one real second is 4 game seconds. A plugin rule of 5 real seconds (50 failed paths) shows as 20 s in the drift table. Log the height too (`y`, `ry` in the samples).
- A test player that stands on a unit (same x and z) picks that unit with every ray: `pick_unit` takes the nearest unit within 0.8 blocks of the ray, also at the eye. Put the eye 2 blocks to the side (`tests/test_pointing.py`, #989).
- A new `gather.Gather` starts with the AoE2 resources `gather.START` (#973): a test that counts gathered or paid amounts from 0 passes `start={}` (also to `bot.Bot`, which hands its keywords to its `Gather`).
- After `kill UUID` the mob plays its death animation for about 1 s, and `data get entity UUID Pos` still finds it: a test that checks that a unit is gone waits a few seconds (#967).
- `Replay.run` ends at the time of the last timeline event, as the record: a walk or a queued unit after it never comes (#978). A unit test whose last event starts a walk or a training needs `run(..., finish=True)`.
- A path of a horse (2 x 2 blocks) up or down a slope at an angle goes in L steps (no diagonal step up): at replay speed it swung from side to side, stepped onto the corner of a block and fell back (54 % up, 18 % down on a test slope). The plugin `steer()` aims at a point up to 3 blocks ahead and cancels the push of the Minecraft MoveControl toward the next point (#1022). A test mob summoned on a slope must stand on flat rows: a 2 x 2 mob on a step is inside the next block and suffocates.
- A screenshot of a live replay with `mc_shot.Client` (#718): send `gamemode spectator aoe2mc` just before each `tp` and shot, not once at the start: the replay or the data pack puts the player back in adventure mode (hearts, hotbar, and the camera stops in trees). The trees of the replay (`v.tree`, `Map.trees`) are in tiles: multiply by `r.T` for a camera position.
- A siege unit is a minecart with a crew: no mob of it is a `RangedEntity`, so `aoe range` on it answers "Range: 0 units" and the unit never shoots. Only a range with a blast (the Mangonel line, #1050) gives its carrier pig the goal `aoe_range`; check "Range: 1 units" in a test of a new ranged siege unit.
- `train.census` (each 2 AoE2 seconds) removes each villager without a position from `Gather.villagers` (#1039): the fake server of a unit test must answer `data get entity U Pos` for each villager that it keeps, also for a trained one (add it to `FakeServer.entities`).
- `Replay.run(to=T)` jumps to T at the start; it is not an end time (#1056). A unit test that stops at a time puts a chat event there. With the fake RCON a plugin unit (`ai=True`) gathers only after `LATE`: patch `Replay.arrived` to `True`.
- AoE2 wiki infoboxes show some unit values with the civilization bonus (#1041): the tooltip `{{tt|65|base 54 - increased by civilization bonus}}` names the base value that `combat.STATS` takes. The MediaWiki API needs the `User-Agent` of `refimage.HEADERS` (the urllib default gets 403).
- A velocity that `AoePlugin.steer()` sets each tick to a path point ahead held villagers (0.6 blocks wide) in place for up to 50 s on flat ground in a town: the line cut the corner of a building (#851). A mob of less than 1 block steers only on a slope (`slope()`). After a change to the walk of all units, also compare the time that units stand still with an order (less than 0.3 blocks between two samples of a `replay_drift.py --log` file) before and after: the table did not show it.
- A horse that `steer()` or `glide()` moved past path points still has them in its Minecraft path: after the arrival it walked back up the slope to them. `follow()` stops the path of a horse at the arrival (#1078). A goal at a block corner (x, z integers) puts a horse 1.4 blocks from it (its path point center is the corner + 1): the replay sends block centers, and a test must do the same. A tamed horse with a NoAI zombie rider at rest moves 0.27 blocks forward and back each tick.
- A mob wider than 1 block (a horse: 1.4) misses its path points up a slope on Paper: it stands 1 block above the point and turns back (#1022). The attribute `minecraft:scale` 0.7 (width < 1) walks up at the flat speed; the owner decides the look in #1096. Measure a climb with a stone slope in the air and `ai.move`, not with the record.
- The 0.27-block jitter of a horse at rest (#1078) does not reproduce (#1132): after `aoe moveto` down the slope of `tests/test_replay_descent.py`, on flat ground, and with no order, the horse moves 0 blocks in 1 s, also with the plugin of #1129. `tests/test_horse_rest.py` checks it. Sample `Pos` only 0.5 s after the arrival: the brake slides the horse about 1 block first.
- `gather.Gather` starts with the AoE2 start resources (#973): a stop condition on `g.stock` must count from the stock at the start (`base + loads × carry`), else it is true at once and the villager drops nothing (#1145: `tools/measure_gather.py`).
- The AoE2 wiki page of 18 civilizations (`Aztecs`, `Mongols` ...) is a disambiguation page: read `NAME (Age of Empires II)` through the MediaWiki API (`tools/refimage.py` `API`) for the "Civilization bonuses" section (#1090).
- After a jump of the live replay, `Replay.run` must not keep a `moving` or `working` time before the jump time: the loop catches each one up and sets the boss bar to that older second (#1125). A villager in `arriving` (Paper, #766) gets only `WAIT` per `steps()` call.
- `run.Game` starts the server on the world folder itself (`--universe`), and the server saves into it: a second check on the same folder starts with the felled trees and the moved units of the first one. Convert again before each run (#718, check 5).
- `Replay.catch_up` (#1168) speeds up the next leg of a unit that is behind, and a walk less than `RECENT` after the last one. The villagers of `de-64.3` still lag 7 to 10 blocks at a constant distance through whole walks, and `--every 2` samples show that lag at the leg start. It is not the walk speed (a villager on flat ground walks at 12.99 of 12.8 blocks per second at speed 4, and 1.15 to 1.5 times faster when asked), not the start of an order (1 block lost), and not collisions in a group (`team modify pN collisionRule pushOtherTeams` changed nothing).
- A zombie test unit on a floor in the air burns in the sun, and the lost health looks like a hit (#1111: an own militia lost 7 next to a shooting town center): `time set midnight` first. A check with a phase "the enemy walks next to the unit" must wait for the walk: 46 blocks take 13 s at the militia speed (#1108).
- `/damage` on the target slime of a building (`combat.building`) says "Target is invulnerable": the plugin keeps the hit points. Destroy a building in a check with `aoe destroy <uuid>` (#1137).
- A client screenshot (`mc_shot.Client.shot`) at once after a `title` command shows no title yet: wait 0.5 s (the title stays about 4 s). The toast "Chat messages can't be verified" covers the top right for about 6 s after the join: wait before the first image. Put the camera of a check outside all footprints, else the player suffocates (#1138).
- A training menu (`aoe menu`) with its queue row is near the 1446 RCON bytes already (URL-encoded: a space is 3 bytes, "·" is 6): a new text for each item does not fit. Send a fixed text once with `aoe lore` (#1160) and keep the menu command short.
- Test the arrows of a building (`aoe building` with an attack) with its design blocks, not an empty box: the plugin shot from above the roof center, and each arrow stuck in the own roof (#1202). Count `@e[type=arrow]` and read their `Pos` and `inGround` when a target takes no damage.
- A mob with `NoAI` does not move, but the pushes of the mobs on its place still add to its velocity: at `setAI(true)` it flies off with all of it (8 villagers on one cell for 12 s flew 20 to 60 blocks, #1168). Clear the horizontal velocity when an order turns the AI on (`AoePlugin.unit`).
- A mob in water moves at about 0.3 blocks per second with a plugin order, and it cannot leave the water at a bank 1 block above the surface (it floats 1.5 blocks under the top; Minecraft lifts it only when 0.6 blocks up are free): its path ends in the water and the order fails after 5 s. `unit()` sets `water_movement_efficiency` 1 and `climb()` jumps it out (#1208). Measure a water walk only between the water and the bank (`tests/test_walk_water.py`): the land part hides the difference.
- A fake-server test of a shooting building (`aoe building ... 5 32 24`) does not show that its arrows hit: a tall watch tower and a near target made a steep shot that hit the own roof edge (#1219). Run its `-m mc` shot test; an arrow that stays next to its start (`data get entity @e[type=arrow,limit=1] Pos`) hit the building.
- After a game mode change, Paper can keep the old sneak state of a player: `PlayerToggleSneakEvent` then misses the next press of the sneak key. Read the key from `PlayerInputEvent` (`getInput().isSneak()`, the change of the client input), as `Viewer.java` does (#1213). Test key taps with xdotool held 0.15 s with 0.15 s gaps: software frames are slow, and a shorter gap is lost.
- A second `run.replay` on a world that the Paper server saved once (the first check run) hung after the jump for 20 minutes (#1087, check 2): convert a new world for each replay run. In a check script, find the slot of an item with `execute if items entity NAME hotbar.N ITEM` ("Test passed"), not with a regex on `data get entity ... Inventory` (the components hold nested braces).
- A `MapRenderer` on the locked map 0 runs only when Paper sends the map data again, and Paper does that only for dirty data: the renderer drew nothing after `addRenderer` (#1237). Call `Player.sendMap(view)` for each player who holds the map (a timer task). `MapCanvas.setPixelColor` with a text color picks the nearest map color (`#FF5555` gave orange): set the exact byte of `aoe2mc.MAP_DYES` with `setPixel`. Without a client no map renders: test the render path with `mc_shot.Client` and `item replace entity NAME weapon.mainhand with minecraft:filled_map[minecraft:map_id=0]`.
- A converted scenario names its trade carts `TRADE_CART_EMPTY` and `TRADE_CART_FULL` (AoE2ScenarioParser), a trained one `TRADE_CART`: match them with `startswith(trade.CART)`, not `==` (#1253).
- `Pathfinder.stopPathfinding()` does not stop a fast mob at once: its velocity carries it on (a husk at replay speed 4 slid 0.85 blocks, #1292). Set the horizontal velocity to 0 too. The server log of a test is in `game.folder/logs/latest.log` while the `run.Game` is open: the folder goes at the exit.
- In a check script, the map item of the replay is not always in the off hand at 0:30, and a jump of the replay fills the hotbar again (it overwrote a map in slot 1): put the map in an empty slot (5) once, and select that slot (#1239).
- `gather.Map` skips the `aoe2mc.PASSABLE_OBJECTS` (`FISH`, `DOLPHIN`, `BOX_TURTLES` ...) before the resource checks: a new resource of that list needs its own branch before that test (`Map.fish`, #1283).
- `NoAI:1b` on an enemy at the start of a check does not hold: a hit (`attackBack`) or its sight (`watch`) gives it a target, and it walks after it. In #1204 an enemy followed the villagers into the passage under the town center (#865), the town center shot at it through the own roof, and the check measured 0 damage on the enemy that it watched (#1285). Print the positions of all enemies in a damage check.
- A world that a check script ran on once has the saved entity positions: convert a new world for each experiment (#1285).
- `Mob#setTarget` of the plugin fires no `EntityTargetEvent`, and a mounted unit has its target on the rider, not on the horse: read `(rider(mob) != null ? rider(mob) : mob).getTarget()` and call `fight()` after a plugin target (#1334: `aoe where` said "no fight" for a scout cavalry that chased an eagle scout).
- The AoE2 wiki page `Repair` does not exist (the API gives no `parse`): the AoE2 II repair values are on `Villager_(Age_of_Empires_II)`, section "Repairing"; `Repairing` mixes the values of all games (#1330).
- The help line of the live replay (`replay_input.help_text`, one `tellraw` with a click for each action of `actions()`) uses 1442 of the 1446 bytes of one RCON command: a new action that needs the plugin goes into the menu only, as `MENU`, `SPECTATE` and `VIEW` (#1303).
- The path follow of Minecraft (`PathNavigation.followThePath`) runs after the plugin tasks of a tick: it can pass the next point in the same tick, and the input then pushes toward the point after it. A prediction of `steer()` from the next point gave a wide mob 27 % more speed to the north-west; take away the real push of the last tick instead (the move less the set velocity, #1344).
- A horse or donkey (trade cart, mounted units) that eats grass (`AbstractHorse#isEatingGrass`, 1 of 300 ticks on a grass block) or rears is "immobile": for 50 ticks it has no AI step, so no path follow, but `steer()` moves it on. More than 2 blocks past its next point, Minecraft never advances the path index again: at the end of a partial path `moveTo` gives back the same path (not done), and the order fails ("no path", #1359). The plugin stops the eating of an ordered horse.
- The UUID of a siege unit in `g.soldiers` is its minecart, and its name line is on the crew (`Passengers[0]`): `aoe label` on a minecart now takes the crew (#1352: an upgraded mangonel kept the name "Mangonel"). Check a name with `data get entity UUID Passengers[0].CustomName`.
- A new armor class of `combat` (`HSI`, `RAM`): a word of `a-z` only. `aoe stats` takes the classes as one argument (a space splits it), and the stats tests match `[a-z,]+` (#1402: `heavy_siege` failed them). Check each AoE2 value of a ticket on the wiki: #1402 also found the scorpion attack 11, not 12.
- Two AoE2 wiki pages can give different numbers: "Scorpion" (Trivia) says the bolt flies 3 tiles past its range, "Pass-through damage" says "Range+2 tiles in total". Take the page of the mechanic, and name it in the code (#1401).
- The crew of a raft (`bamboo_raft`, the demolition ship) sits about 1 block higher than the crew of a boat, and the range goal of the plugin measures in 3D: a reach of 2 blocks never fired at a boat 2 blocks away (#1440). Give a ship's contact reach at least 1 tile, and print `data get entity ... Pos` of both crews when a ship does not shoot.
- `Gather.where` (`aoe where @e[type=!player,team=!]`) also answers the building targets (slimes on team `p<n>`): put their `combat.target_uuid` in `want` to know which buildings stand, with no extra command per building (#1470).
- `Replay.building` gives no commands for a footprint with no land in it or next to it (open water): a fish trap passes `water=` (the ground y, `build.found`, #1438). A ticket can give the AoE2 (1999) value: the fish trap rate is 0.35 food/s in DE ("Fishing Ship" text), not the 0.21 of the trivia list.
- A build of the plugin by hand (`game/plugin/gradlew jar`) fails with "release version 25 not supported" under the default Java 21: set `JAVA_HOME=/usr/lib/jvm/java-25-openjdk-amd64` (`run.build_plugin` does it). A screenshot of a damaged building: do not use the blacksmith, its target slime burns and covers it with the fire texture (#1526, #1522).
- Paper 26.3 writes a join as `[09:50:50 INFO]: System chat: \x1b[93mone joined the game\x1b[0m` (color codes when stdout is no terminal): `run.JOINED` missed it, and no player got `op` until #1310. Test a log pattern with a line of a real server.
- `run.Game` uses the world folder in place: a second server run on the same converted world timed out in `forceload` (RCON `TimeoutError`) and gave ticks of 8 to 13 s. Convert a fresh copy for each check run (#1310).
- `team list pN` names the units too (they are on the teams) and the server cuts a long list with `...`: test the team of a Minecraft player with `execute if entity @a[team=pN,name=X]` (#1310).
- `run.Game(W)` saves the world into `W` when it stops: a second check run on the same folder has the entities of the first run (`@e[tag=own,limit=1]` reads the old one). Convert or copy a fresh world for each run (#1327).
- A check screenshot with `mc_shot.Client` on a server: put the player in adventure mode and `attribute aoe2mc minecraft:gravity base set 0`, then `tp` stays in the air. A spectator sees the invisible target slimes of the buildings as large blue boxes (#1327).
- A compile check of the plugin by hand: `JAVA_HOME=/usr/lib/jvm/java-25-openjdk-amd64 game/plugin/gradlew --no-daemon -q jar` (in `game/plugin`); the default `java` gives "release version 25 not supported". A field initializer of `AoePlugin` that reads a later field fails with "illegal forward reference": write `this.field` in a lambda (#1567).
- A flare from the Game menu needs the map ground: `flare.from_look` uses `Map.pick_ground` (the "ground" of `aoe2mc.json`), so on a test floor in the air (`fill ... y 200`) it gives no flare and no error. A menu click closes the Game menu by itself: an `Escape` after it opens the pause menu, and the next keys (`t` for the chat) go there (#1235).
- No NBT stops the Drowned conversion of a zombie (`DrownedConversionTime`, `InWaterTime` only start or reset it): cancel the `EntityTransformEvent` (reason `DROWNED`) in the plugin. The Paper API has no path malus; the server has the Mojang names (`Mob#setPathfindingMalus(PathType, float)`), but `PathType.WATER` is also the 1-block shallows (#1658, #1669).
- `tests/test_gather.py` `FakeServer` moves an entity only on a bare `tp UUID X Y Z ...`, not on `execute as UUID at @s run tp @s ...` (`replay.sail`): after `fleet.tick` a ship has its new `g.ships[u].pos`, but `g.pos(u)` still gives the start. Set `server.entities[u]["Pos"] = g.ships[u].pos` before code that reads `g.pos` of a ship (#1652).
- A zombie path (`Mob#getPathfinder`) goes around deep water when a land path exists (the water malus 8 is enough), but with no land path it walks on the floor of the water: test "no water" with a lake across the whole floor (`tests/test_walk_deep_water.py`, #1669). Paper has no malus setter: the plugin calls the Mojang names (`getHandle`, `Mob#setPathfindingMalus(PathType, float)`) by reflection.
- A world that `run.Game` (Paper) saved does not load in `tools/mc_shot.py` single player: "Errors in the currently selected data pack(s)". Take the images of a game state with `mc_shot.Client` on the running server (`gamemode spectator aoe2mc`, `tp aoe2mc X Y Z YAW PITCH`, `client.shot()`), #1655.
- `Pathfinder#findPath(goal)` sets the target of the vanilla navigation: a `moveTo(goal)` after it, while the last path still runs, takes that old path again (vanilla `createPath` keeps a path that is not done when its target is in the set), so the unit keeps its last order (#1713: the scout of `tests/test_replay_climb.py` did not walk back down). Call `stopPathfinding()` before a `findPath` of a new order.
- A vanilla trident of a drowned (a chakram, a skirmisher) can miss its target (aim spread of `Drowned#performRangedAttack`). A unit with AoE2 accuracy 100 % takes the damage in `RangeGoal`, not from the projectile (#1713).
- `tests/test_menu.py` `test_gather_reads_the_menu_clicks` builds a bare `Gather.__new__` with only the attributes that `clicks()` uses: a new attribute that `clicks()` reads must go there too, else the full suite fails with AttributeError (#992).
- In tests, `from game import build` and the bare `build` that `game/*.py` import are two module objects: a table that `train.py` changes at import (`build.AGE |= ...`, #1082) is only in the bare one. Read it through the importer (`train.build`).
- `Gather.bots` holds `bot.Bot` objects, not `Gather`: read a Gather attribute of a bot (`sites`, `stock`, `villagers`) through `b.g` (#1220: `wonder.found` read `b.sites` and stopped each game with a bot; only `-m mc tests/test_bot_gather.py` found it).
- `tests/test_siege_walk.py` `summon()` seeds the UUIDs with the length of the tag: two units with tags of the same length fail with "Unable to summon entity due to duplicate UUIDs" (#1386). Use tags of other lengths.
- A new item in the menu of a training building changes the exact menu strings of other tests: `grep -ln "aoe menu Steve <Label>" tests/` (#1397: the archery range in `test_age_lock.py`, `test_train_archery.py`; the stable in `test_train_stable.py`) and fix them in the same PR. A help line (`train.HELP`) has at most 50 characters (`tests/test_menu_help.py`).
- `train.TRAINS` holds the items of a building in one tuple line: parallel tickets that add to the same building conflict there (#1362 and #1352, #1375 and #1374). Put each new item on its own line of the tuple, and take a free menu slot of `train.ITEMS` (`grep '"<BUILDING>"' game/train.py` first: #1375 and #1374 both took slots 2 and 3).
- A building that trains no units (university, blacksmith, mill) has no `RALLY` item: slot 8 of its first menu row is free for a technology (#1490). A test that reads the end of a `train.TRAINS` tuple (`[-2:]`) breaks with each new item: test the order with `index()`.
- `tests/test_combat_blast.py` and `tests/test_siege_min_range.py` compare the whole `combat.BLAST` and `combat.MIN_RANGE`: a new unit with a blast or a minimum range changes them too (#1484). `grep -ln "combat.<TABLE> ==" tests/` before the fast suite.
- The first menu row has 8 item slots (0-7, slot 8 is `RALLY`), and the dock had all 8 after #1481: put a next item in `train.MORE` (slot 18 and on, the row under the queue row 9-17, #1485). Look at `grep -n "\"<BUILDING>\"" game/train.py` and the slots of its items first.
- A new item of the town center menu in the Feudal or Castle Age breaks the `endswith(... + RALLY)` asserts of `tests/test_wheelbarrow.py`, `test_castle_age.py`, `test_imperial_age.py` (the constants `IMPERIAL`, `CASTLE`, not the label): the grep for the label does not find them; run the fast suite (#1454).
- Two runs of sibling tickets of one menu (#1505, #1506) took the same free slot (`MORE`) at the same time, and main went red (#1551): `tests/test_train_knight.py` checks one item per slot only on the merged code. A refill that makes several menu tickets of one building writes the slot of each item into its ticket body.
- A test that reads the values of an `aoe building` command reads them by position from the start (`split()[12]` attack, `[13]` range, `[15]` minimum range): the classes and the bonus at the end change with new classes (the towers got `stone` in #1590, 11 tests broke).
- Do not add a field to `combat.Stats` for a new value of a technology: about 50 tests compare `combat.stats(NAME)` with a plain tuple and fail. Give the value as an argument (`combat.building(..., low=build.minimum(g, name))`, #1547).
- `gather.Map` is square: `n` is the row count of `grid()`, so a test map wider than its rows has no cells past `n` (`free` is False there). A non-square test map hid the bug of #1694: the test passed on the old code. Make test maps square.
- AoE2 values (hit points, attack, `ROF`, armor) of a unit or building: the MediaWiki API `api.php?action=parse&page=NAME&prop=wikitext&format=json&redirects=1` (User-Agent of `tools/refimage.py`) gives the infobox fields. A name of several games is a disambiguation page: use `Watch_Tower_(Age_of_Empires_II)` (#1112).
- The cost and time of a unit upgrade (Man-at-Arms → Long Swordsman) are `UpCost` and `UpTime` in the infobox of the unit before it, and most unit names are disambiguation pages: ask for `Long Swordsman (Age of Empires II)` (#1396).
- A technology ticket can name a technology that AoE2 DE removed (Supplies, update 141935, #1418): read the `Removal` field and the `Required` field of the infobox first. A missing `Required` technology (Fishing Lines for Gillnets) goes into the same PR, else the item is never in the menu (#1439).
- A technology ticket can name an old building: read the `Building` field of the infobox (`{{tt|NEW|OLD before ...}}`). Update 169123 (The Last Chieftains) moved Careening and Dry Dock from the dock to the university, with new costs and effects (#1441).
- The wiki availability chart (`{{AoE2 tech availability`) of a technology: `0` = the civ does not have it, `1`, `+` or `-` = it has it; `Default` is the value of each civ not in the list. For `civs.MISSING`, take the civs with `0` (with `Default = 0`: all civs minus the listed ones, #1504).
- In the same chart `-1` also means missing (removed: the Lithuanians and Poles in the Hussar chart, the Chinese in the Camel Rider chart, #1550); `x`, `+-` and `-+` mean it has it.
- An AoE2 value in a ticket can be wrong (#1113 said an empty town center shoots 1 arrow; the wiki infobox says 0, #1201): check each AoE2 number of a ticket with the MediaWiki API before the code.
- A unit that dies with no attacker (about 2 HP per real second, `Fire` 0, `Air` 300, `HurtTime` > 0) suffocates in a block: look for a site footprint on it (`g.sites`, #1769). RCON cuts a long `data get entity U`: ask for one path (`data get entity U Health`).
- The tables `train.COSTS`, `TRAIN_TIMES`, `TRAINS`, `TECH_AGE`, `AFTER`, `ITEMS` and `HELP` come from `game/data/train.jsonl` (#1702): add a new menu item as one line at the end of its building block (the line order is the order of `TRAINS`), not in `game/train.py`. `merge=union` keeps the lines of both sides of a merge.
- A left click of a real client (`client.xdo("click", "1")`) on Paper: on air and on a block the plugin gets `PlayerInteractEvent` (`LEFT_CLICK_AIR`, `LEFT_CLICK_BLOCK`; cancel it, and a creative player breaks no block), on a mob `EntityDamageByEntityEvent` with the player as damager. Vanilla has no event for it (#992, #1788).
- The target slime of each building (`combat.building`, tag `aoe2mc.building`) is a living entity in the team `p<N>`: code that loops over the living entities of a team (minimap dots, counts, `@e[team=...]`) must skip that tag, else each building counts as a unit (#1800: an enemy building showed through the minimap fog).
- A chat line "[Server: …]" in a game: a console command of the plugin (`Bukkit.dispatchCommand(Bukkit.getConsoleSender(), …)`) goes to all operators, and each player is one (`op_joined`): `run.properties` turns off `broadcast-console-to-ops` and `broadcast-rcon-to-ops` (#1799). A check script that prints the last 5 client chat lines finds such text (#1138).
- `@e[team=!]` misses the units of a fresh world: the datapack pulse puts them in their team some seconds after the start (`Where 0` in a test that selects at once, #1769). The UUID of a mounted unit in `aoe2mc.json` is its horse (the root vehicle); a `/tp` of a rider dismounts it: move the vehicle (`execute as U on vehicle run tp @s ...`).
- A real-client check (`mc_shot.Client`) that aims with `tp aoe2mc X Y Z YAW PITCH` above the ground: the player falls in about 1 s, so the look changes before the click. Put a `barrier` block under the feet first (#1815). `xdotool mousedown 3` and `mouseup 3` give a held right click of the command stick.
- A click on a chat line with `mc_shot.Client` (GUI scale 3, 1280 × 720): the last line is at y = 720 - 40 × 3 - 9 × 3 // 2 (587), after `key("t")`. A `run_command` click of a command with a permission can show a confirmation screen: give the click its own plugin command with no permission (`aoego`, #1816). A teleport in creative mode does not fly: the player falls; call `setFlying(true)` when `getAllowFlight()`.
- The hit points of a building in a game: `scoreboard players get <target UUID> aoe_hp` (`combat.target_uuid(footprint)`; the plugin keeps them there, not in the slime health). With the number of attackers this measures the AoE2 damage rate in a check (#964: 4 militia, 8.6 HP/s from a dock).
- `mc_shot.Client`: `key("3")` did not change the hotbar slot in two runs (#1830): turn the wheel (`xdo("click", "5")`, one slot per click, some get lost) until `execute if items entity NAME weapon.mainhand ...` passes. `data get entity NAME Inventory` comes back cut ("...") over RCON: test an item with `execute if items`.
- An exception in a scheduled task of the plugin (`watch()`, `hold()`) only prints "Task #N generated an exception" in the server log, and the task fails each second: a test then only sees "nothing happens". `run.Game` deletes the server folder with its `logs/latest.log` at the end: copy the log first (patch `run.shutil.rmtree` in a scratch script, #1820). `calm(a, b)` with b without a side (the crew of a siege unit) threw an NPE there.
- `test_siege_walk.summon` seeds the UUIDs with `len(tag)`: two units with tags of the same length give "Unable to summon entity due to duplicate UUIDs" (#1820).
- A unit in a `train.tick` test starts only with population room: `test_forging.setup()` has a town center and 4 units (limit 5), and `census()` sets `g.pop` again, so `g.pop = 0` does not help. Add a complete house to `g.sites` for a second unit (#1894).
- The text of a wiki page (the "Civilization bonuses" list): `refimage.query()` always sends `action=query`, so `action=parse` gives a TypeError. Call `refimage.fetch(refimage.API + "?" + urlencode(dict(action="parse", page=P, prop="wikitext", format="json", redirects=1)))`. Page names: "<Name> (Age of Empires II)" (the bare name is a disambiguation page), the Chronicles civilizations "<Name> (Chronicles)" (#1896).
- A menu slot: 0-7 are the first row, 8 is "Rally point" (`train.RALLY`) of each building that trains units, 9-17 the queue row (`train.ROW`): a new unit of a full first row goes to the row from 18 (`train.MORE`, the missionary at slot 21, #1939). A test without a civ sees all civ-only items (`civs.civ` is None).
- A plugin that reads a file of the converted world (`aoe2mc.json`): `World#getWorldFolder()` on Paper 26.3 is not always the folder that holds it (a world loaded with `--universe` and `--world`): look in the parents too, as `Minimap.ground` does ("Minimap: on" without "bare ground" showed it, #1940).
- The player of a check script (`mc_shot.Client`, adventure mode) falls after each `tp`: a fall from 30 blocks kills it, and a wall that the villagers build around it suffocates it. A dead player keeps its last position, so the next `tp` and `Gather.look` fail without an error, and a player next to a gate keeps the gate open. Give it `effect give NAME resistance infinite 4 true`, `tp` it to the ground away from the sites after each click, and take images from a spectator (#1327).
- A module that keeps its state on a `Gather` with `vars(g).setdefault(KEY, ...)` must not use the name of a `Gather` method as KEY: the instance attribute hides the method (`herd`, #1840). `grep -n "def KEY" game/gather.py` first.
- A new ship or siege unit changes the snapshot tests of the tables: `BLAST` (`tests/test_combat_blast.py`), `MIN_RANGE` (`tests/test_siege_min_range.py`), the length of `combat.SIGHT` (`tests/test_building_data.py`), an `"upgrade"` key (`tests/test_train_upgrade_key.py`). Run them before the full suite (#1935).
- An own ship moves with `fleet.py` /tp steps: read its cell from `g.ships[u]` (`Villager.cell`), not from `g.positions`: the fake server of `tests/test_dock_train.py` has no entity for a trained boat, so `garrison.tick` dropped the ship at once (#1949). A boat on a dock or other footprint without "ground" needs `g.map.sea(x, z)` as its y: `g.map.y` gives None there, and `or 0` put it at y 0.
- A check script of two people that calls `run.play(..., people=2)` in a thread: set `run.Game.people = 2` before the clients join, as `main()` does. Else `Game.side` gives no team to the players who joined first, and no click reaches a `Gather` (#1938). Run `play` with `daemon=True` and read the thread for an exception: a crash in the loop (#1980) stops all training and clicks without a message in the client.
- `game/data/civs.jsonl` has one line per civilization and `merge=union`: a merge of two branches that both change one civilization keeps both lines, and `table.load` stops ("more than one line"). Take main's file (`git show origin/main:game/data/civs.jsonl`) and apply your names again with a script; a new building or unit also changes the counts in `tests/test_building_data.py` and the menu lists with no civilization (`tests/test_train_archery.py`, `tests/test_age_lock.py`, #1952, #1930).
- A train-time bonus of a civilization (`civs.TRAIN_RATE`) changes the "N s" of the menu tests that use that civ: `grep -ln "CIV" tests/*.py | xargs grep -l " s · queue"` before the full suite (#1927: the Aztec eagle and jaguar tests).
- A test that reads the price of a regional unit in the menu: some of its civilizations have a cost discount (`"costs"` in `game/data/civs.jsonl`, the Incas pay 38 food for a 50-food slinger): check the price with a civilization without one (#2010).
- The effect of a technology is the key `"effect"` of its line in `game/data/train.jsonl` (#2029), not a lambda in `train.TECHS`: `{"if": [{"class": "infantry"}], "add": {"attack": 4}}`, `{}` for no combat change, or the name of a function of `train.py` for real logic (`train.effect()`, `train.test()`). A line without `"effect"` is not a technology: a branch that still adds a `TECHS` line gets a merge conflict there; move the lambda into the key.
- The `tiny_world` fixture has a world border of 96 blocks (0 to 96): Minecraft path finding takes no step outside it, so a melee mob on a test floor past it never reaches its target, and a ranged one still shoots. A test floor outside 0 to 96: `worldborder center` and `worldborder set` first (#1968).
- An exception in a plugin loop (`siege()`, `watch()`, `hold()`) stops the loop for that tick, so the units after the one that throws (in `HashMap` order: random per run) do nothing, and a server test fails for other kinds each run. Search the server log for "generated an exception" first (#1968: `Mob#attack` on a chicken without `attack_damage`).
- A wiki availability chart (`{{AoE2 tech availability`) has no line for the Chronicles and new civilizations that are not in its list (Achaemenids, Athenians, Spartans ...): they take `Default`. A technology with `Default = 0` goes into the "missing" list of each such civ too (#2136). A university technology costs the Italians 25 % less: a menu test of the cost uses another civ.
- A regional unit that replaces a common one shares its menu slot (dock slot 19, the armored elephant in slot 0 of the battering ram, #2139): the civs without it list it in `"missing"`. A test without `g.data["players"]` has no civ and shows both lines, so a test that counts the items of a menu (`count(":gray_dye:")`) breaks: test the names of the items.
- A walk speed measure on a server: `tp` a unit back to the start does not stop its `aoe moveto` order (it stops about 1.3 blocks short of the goal, and the order stays), so the unit walks back to the old goal and the times mix. Give each round a new goal from the current position (+8, then -8 blocks) and time the first 6 blocks (#2057).
- A menu test that compares the whole menu text, or counts all gray items, breaks with each new unit of that building, and parallel unit tickets conflict there: check only the own item (`item()` and `labels()` of `tests/menu_line.py`, #2187; the Castle Age count in `tests/test_siege_train.py`, #2141, #2156).
- `tools/data_lint.py` counts the AoE2 names in the whole `civs.RULES` dict, also in its lambdas: a second name (`n == "SLINGER"`) fails `test_game_names_in_code.py`. Give the units a tag in the key "groups" of `game/data/units.jsonl` and use `tagged(n, ...)` (#2116).
- Parallel unique-unit tickets take the same free slot of a menu (the Temple Guard #2157 and the Ibirapema Warrior #2158: barracks slot 23). Just before the push, `git fetch origin main` and list the slots of the building in `game/data/train.jsonl`; the menu shows the items in file order, so put the new lines at the end of the block.
- A server test that hurts an enemy unit: the target hits back (the default stance, #733: a galley shoots its attacker), so do not assert the full hit points of the attacker; use a unit out of the fight (#2165).
- A new key of a line of `game/data/civs.jsonl` (`"arrows"`, `"hp"`): the code must read it (`tests/test_data_keys.py`, #2188), and add it to `check` of `tests/data_checks/civs.py`; a new table of `game/civs.py` for `tests/data/civ_bonuses.jsonl` "in" also goes into `TABLES` of `tests/test_civ_wiki.py` (#2178).
- A unit whose values grow with each age (Flemish Militia): give `CASTLE_AGE` and `IMPERIAL_AGE` a list `"effect"` (one change per unit, `train.effect`), and a shorter train time from an age the key `"faster": [age, seconds]` of its line in `game/data/train.jsonl` (`train.FASTER`, #2155).
- `gather.Gather` has many short attribute names (`carry` is the villager load limit, `tick`, `chop`): grep `self.NAME =` in `game/gather.py` before you add one. A new `self.carry = {}` broke 48 tests through `limit()` (#2111).
- A new regional unit of a menu (#2133): a Dark Age unit has no line in `game/data/build.jsonl` (`"age": 0` fails `test_data_files.py`).
- `build.found` in a fake-server test draws the design with `Replay.building`: the map data needs `level_height` (the `grid()` of `tests/test_gather.py` has none, KeyError), and stone and wood in `g.stock` (#2129).
- A test must not assert a literal cost, train time or age of `game/data/train.jsonl` (`train.COSTS["X"] == {...}`): `tests/test_conflict_prone.py` fails on it (#2182). Older tickets still ask for "the wiki cost, time and age" in the test: check the menu label, the queue and the stock change by `train.COSTS["X"]` instead (#2191).
- A bonus of `tests/data/civ_bonuses.jsonl` with `"in": TABLE` needs `TABLE` in `TABLES` of `tests/test_civ_wiki.py` (#2172).
- A test must not assert a literal line of sight, stat or walk speed of `game/data/units.jsonl`, `buildings.jsonl` or `replay.jsonl` (`combat.sight("X") == 6`, `replay.SPEEDS["X"] == 1.35`, `combat.stats("X") == (...)`): `tests/test_conflict_prone.py` fails on it (#2223). Check a behavior that the code computes from the value.
- A new key of `game/data/civs.jsonl` since #2281: one line in `game/data/civ_keys.jsonl`, read it with `civs.value("key", civ, default)` where the bonus applies; `tests/data/civ_bonuses.jsonl` "in" can name the key. No new table line in `game/civs.py`.
- `./gradlew jar` in `game/plugin` by hand: the session `JAVA_HOME` is JDK 21, so it fails with "release version 25 not supported". Set `JAVA_HOME=/usr/lib/jvm/java-25-openjdk-amd64` (`run.build_plugin` does it, #2248).
- A field of the plugin record `Stats` with a default: add a second constructor without it, so the other `new Stats(...)` stay (#2248). `tests/data/civ_bonuses.jsonl` allows one state per bonus: a bonus with a part that is done needs `"in"`, even when another part (Bengali conversion) is not.
- `civs.missing(g, "MANGUDAI")` is False for each civilization: a unique unit without an elite upgrade in `train.COSTS` is not in `civs.MISSING`; the castle trains only `train.UNIQUE` of the own civ. Test a unique unit with `train.trains(g, "CASTLE")`, or with one of `train.own_civ_only()` (#2298).
- A fake server that keeps the mobs of `train.summon` must read `UUID: [I; a, b, c, d]` with spaces (the SNBT of `units.make_entity`): a regex without them finds no mob, and `g.pos` then gives None (`tests/test_mule_cart.py`, #2209).
- A death and its killer: the Python side sees only own units that vanish (`train.census`) and fallen targets of attack orders (`Gather.fall`); only the plugin sees the killer (`AoePlugin.harm`, `kill()`: the score `aoe_mounted_kills` per side, #2271).
- The wikitext of an AoE2 wiki page (the bonuses): `refimage.fetch(refimage.API + "?" + urlencode(dict(action="parse", page=P, prop="wikitext", format="json")))`. `refimage.query()` always sends `action=query`: `query(action="parse")` stops with a TypeError (#2333).
- A server test of two melee units on different blocks (a step, #2307): after the first hit the vanilla melee goal walks them off the step or onto it (also with `stand_ground`), so later hits take the damage of one level. Check only the first hit of each unit (the first health below full).
- Carcasses decay in game seconds of each `Gather.step` (`Map.rot`, #2310): a test that loops `step()` with no sleep loses most of the food of a hunt. A test that counts the full food of a carcass uses a Jurchen player (`"civ": "JURCHENS"`, no decay).
- A new value of the key `"units"` of `game/data/civs.jsonl` that is no `combat.Stats` field (`"taken"`, `"friendly"`, #2418) needs its name in the skip tuple of `civs.units()` (else `getattr` fails) and in the value tuple of `tests/data_checks/civs.py`. A unit that gets the `aoe stats` command without the factor (a trebuchet, a refresh after a technology) resets it to 1 in the plugin: pass it at each call of `combat.stats_command`.
- A new `tick` call in `Gather.run`: import its module at the top of `game/gather.py` (not in the loop) and patch it in `loop()` of `tests/test_play_speed.py`, `tests/test_victory_option.py` and `tests/test_regicide.py` (`grep -l "object.__new__(gather.Gather)" tests/`): they build a Gather with `object.__new__` (no `clock`, no `data`), so the new tick fails there unless patched; a lazy import in the loop cannot be patched (#2355).
- An arrow on a ship hits its boat: `AoePlugin.onBoatHit` (`VehicleDamageEvent`) gives the damage, not `onHit`. A change to the damage of a projectile must go into both (#2379: the extra arrow of an Armenian galley did its full damage on ships).
- Paper `Pathfinder#moveTo` with the target of the current path returns that path again while it is not done, also a part of the way that ends before the target: call `stopPathfinding()` first for a new search (#1713, #2303: trained replay units stopped 10 to 20 blocks before their rally point as "no path"). A test that opens a wall during the walk does not show it: Minecraft searches again when a block near the path changes. To see the "no path" lines of `tools/replay_drift.py`, copy `logs/latest.log` of `game.folder` before the `run.Game` block ends.
- A test Gather without a civilization (`test_train_barracks.setup`) shows each regional item of a building: a new barracks item can make the menu longer than one RCON command, and `test_train_barracks.menus` then misses the `aoe menu-add` part (`test_train_spearman.py` lost its Spearman, #2431). Read menus with `test_forging.menus`.
- A new game mode of `--mode`: one line in `run.MODES` (name: help text, alphabetical order), its module, and no change of the comment of the `"mode"` line of `run.SETTINGS` or of the `--mode` lines of `main()`: #2408 changed them and conflicted three times with #2354 and #2407 in 30 minutes.
- `train.tick` runs `train.census`, and it sets `g.pop` again from the live units of the FakeServer: a test of a free unit checks `g.pop` right after one research, not across two `advance()` calls (#2480). `tools/refimage.py`: `query()` always sends `action=query`; for the wikitext of a page call `fetch(API + "?" + urlencode(dict(action="parse", page=..., prop="wikitext", format="json")))`.
- A new unit of `game/data/units.jsonl` also needs an age line in `game/data/build.jsonl` (ages 1 to 3; a Dark Age unit has none), and its test must not copy a stat (`tests/test_conflict_prone.py`). A bonus line of `tests/data/civ_bonuses.jsonl` with two tables: `"in": ["COSTS", "UNITS"]` (#2482). The wiki text of a page: `refimage.fetch(API + "?action=parse&page=NAME&prop=wikitext&format=json&redirects=1")` (`refimage.query` sets `action=query`).
- An in-game check of the game program needs no clicks (#2381): with a `mc_shot.Client` joined, `g = run.play(game, W, seconds=2)` gives the Gather; drive it with `train.queue`, `build.found`, `Gather.build`, `Gather.send`, then `g.run(N)`; a load is `run.restore(SAVE/world, W)` and `run.play(..., state=savegame.read(SAVE))`. Copy the values that you compare (`json.loads(json.dumps(...))`): a dict that holds the live `g.queues` lists shows their later state.
- The mode setup chain of `run.play` (`if settings["mode"] == ...` / `elif`) and the last line of the `form(...)` keys of `check_setup` (now `tests/data_checks/setup.py`, keys in `game/data/setup_keys.jsonl`) conflicted on each new mode: #2406 needed 6 merges of main in 90 minutes. Add a new `elif` branch before `elif settings["mode"] != "standard"`, a new key on its own line before the last line, and do not change the lines of other modes.
- A unit that walks away with no order and no target ("stray" in `tools/replay_drift.py`) can still have its Minecraft path: on a slope `steer()` and `glide()` take the mob past path points that Minecraft does not count, so after the arrival it walks back to them, up to 25 blocks (#2303). The plugin stops the path at the arrival when its next point is not at the goal (`behind()`). To find what moves a unit between two samples, log the state changes of each unit (order, target, a path with no order) in a scratch copy of the plugin.
- A split menu (longer than one RCON command, `menu.commands`) sends its items with the last slot first: a test of the full order (`menu_line.order`) must accept that order too (`test_train_barracks.py`, #2483). `test_loom.menus` joins the `aoe menu-add` parts now, as `test_forging.menus`.
- `Replay.run` wakes only at the times in its `step` list (walks, gather steps, texts, builds): a new timed state of the live replay (`charging`, #2552) needs its time there and in the `while` condition, else `steps()` never sees it.
- A `monkeypatch.setattr` on `from game import X` does not reach `run.play`: `run.py` imports the bare `X`, another module object. Patch the bare module (`import X as plain`, `tests/test_start_buildings.py`, #2429).
- `game/run.py --play` has no `--seconds` option (a ticket "Verify" line can name one): run `timeout -s INT 240 python3 game/run.py W --play --log F.jsonl`; Ctrl-C saves the game and stops the server. A test world with a computer player: convert `four_civs` and set `"computer": true` on player 2 of `aoe2mc.json` (#2543).
- A Paper test of a walk speed: measure in server ticks (`/time query gametime`) from the first step, not in wall clock time from the order. A unit stands 2 to 3 ticks before its first step (the first AI tick, the path search): on a walk of about 1 s that is 10 % of the speed (#2591, `tests/test_replay_descent.py`).
- A real-client click test on a framed map (`tests/test_minimap_click.py`, #2586): a look at an exact pixel edge (x = -0.25 of the frame: pixel 32) gives the pixel before it (31): aim at the middle of a pixel. An RCON answer ends with `\n`: `.strip()` before `endswith`.
- A selector of the unit tags (`aoe2mc.p1`, `aoe2mc.t<id>`, a trigger area) finds the rider of a mounted unit, not its horse: `aoe moveto` on the rider answers "Moved 1 units" and nothing walks. The plugin walks the horse (the `uuid` of `aoe2mc.json`): tag it with `execute as <sel> on vehicle run tag @s add T` (#2647).
- `tools/refimage.py`: `query(action="parse", page=P, prop="wikitext")` gives the wikitext of a page (#2685); the `fetch(API + ...)` lines above are older.
- The key `"units"` of `game/data/setup.jsonl` is a key of the "one kind" rule (`"kind": true` in `setup_keys.jsonl`): a mode with `"level"` (Battle Royale) cannot have it, `check_setup` fails. Give start units of such a mode their own key (`"heroes"`, #2688).
- A summon command of a mounted unit is near `rcon.MAX` (1446 bytes): a new item component on its armor (the equipment assets of the resource pack, #2743) made 223 units too long. `units.summon_snbt()` drops the default tags of `to_nbt` and writes compact SNBT (`UUID:[I;...]`, no spaces); `tests/test_resourcepack_riders.py` checks each unit. A test that changes `units.ASSETS` (or a `run.Game` on a world with the pack) leaks it into later tests: `tests/conftest.py` resets it.
- `game/scenario.py` `orders()`: each trigger order PR added a sentence to its docstring and to its `if new or ...` line, and #2889 got 4 merge conflicts there in 30 minutes. Describe a new order in the docstring of its own function only (#2853).
- A Minecraft attribute that a trigger sets on a unit (`max_health`, `movement_speed`, an `attack_damage` modifier) does not last in the game program: each `aoe stats` and each order sends the AoE2 values again, and the plugin reads no `attack_damage` or `armor`. Store a value order (`aoe2mc.value_lines`, `scenario.values`) and give the uuid to `train.stats(g, name, uuid)` and `train.speed(g, name, uuid)` (#3083). The converter tests of these handlers compare full line lists: leave the order lines out with `test_trigger_unit_values.unit_value`.
- A fake-server test with `g.paper = True` does not walk the villagers: `Gather.go` sends `aoe moveto`, and only the plugin moves them. A test of a gather or drop trip sets `g.paper = False` after the Paper-only order (`garrison.order`, `siege_tower.order`), so that the villager walks its own path (#3007). A new order function calls `Gather.new_order(units)` before it sets its own state (#3007).
- A particle mark that the player sees from the high view of the game program (30 to 50 blocks away) needs `Particle.DustOptions` scale 2 and `force` true in `Player#spawnParticle`: white dust of scale 1 every block did not show in the `mc_shot` image of the sight edge (#3330).
- The rule "only the own civ has its unique unit" is in `train.own_civ_only()` (#1760): `train.py` adds it to the bare `civs.MISSING`. A test that imports `from game import civs` reads another module object without it: read `train.civs.MISSING`, `train.civs.missing(...)`.
- The "queue 0/15" of a train menu line is the queue limit, not the training time: the time is the "N s" part (`test_chakram_thrower.py`, #1724).
- `train.UPGRADES` comes from the key `"upgrade": [OLD, NEW]` of the line of the technology in `game/data/train.jsonl` (#1915): a ticket that says "add a `UPGRADES` line in `game/train.py`" means that key now.
- A new `X.tick(g, dt)` in `Gather.run`: `tests/test_play_speed.py` runs the loop on `object.__new__(gather.Gather)` with no `game`, `data` or `paper`, and stubs only the ticks that it knows. Make the tick return early on a missing attribute (`treaty.holds`, #2297).
- A new field that `game/*.py` sets on a Gather (`g.x =`, `vars(g).setdefault("x"`) fails `tests/test_savegame_fields.py`: save it in a key tuple of `game/savegame.py` (game state), or add it to `savegame.NOT_SAVED` with its reason (a tick timer, a shown thing, a setup value, #2535).
- Since #3122 `train.census` removes each soldier with no position: a fake-server test that puts a unit into `g.soldiers` by hand must give it an entity (`g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})`), else a `train.tick` removes it (KeyError). A live unit then counts in the population.
- `Gather.selected` is the selection of `Gather.person` since #3486 (co-op: each Minecraft player of one AoE2 player selects on its own). `click()`, `box()`, `deselect()`, `menu.clicks` and `hints.state` set the person. Code that removes a unit from the selection of all people (death, new owner) calls `g.drop(u)`, not `g.selected.discard(u)`. A selection that code made with person `""` (a setup, a test) goes to the first named person.
- What the bot soldiers do in `tools/play_check.py`: wrap `bot.Bot.fight` in a script and log `self.targets`, the target kind (`t in g.forts`), the distance, and the hit points (`scoreboard players get T aoe_hp` for a building, `data get entity T Health` for a unit) each 20 AoE2 seconds. Use `Bot.time` as the clock: `recap.game_time` of a bot Gather ignores `--speed` (#3513). A target whose hit points do not drop while its soldiers stand still is a target that they cannot hit (#3441).
- A building arrow that does no damage: count the arrows and read their place (`execute if entity @e[type=arrow]`, `data get entity @e[type=arrow,limit=1,sort=nearest,x=X,y=Y,z=Z] Pos`). The invisible target slime of an own building does not stop an arrow; a block does, and the arrow stays in it (#3562: 30 arrows in the wall of a house between the town center and the militia). `AoePlugin.start` then starts the arrow above the target.
- A mob with a brain (a hoglin; also a piglin, an axolotl, a warden) gives null for `Mob#getTarget` after `Mob#setTarget`: it reads the attack memory of the brain. Use `target(mob)` and `setTarget(mob, t)` of `AoePlugin.java`, not the API calls (#3624: the hoglin bears did not hunt).
- AoE (1) values on the AoE wiki: the page name ends with " (Age of Empires)" when an AoE2 page has the same name (`Granary (Age of Empires)`, but `Storage Pit (Age of Empires)` and `Clubman`: check with `action=query`), a technology has a `{{Techbox`, a unit an `{{Infobox AoE2 unit`. `tools/refimage.py box PAGE...` reads both; `refimage.query(action="parse", ...)` gives a KeyError for a missing page (#3665).
- A villager that flips between two orders (a `walk` and an `idle` event of `run.py --log` in the same tick, #3726): in a `git worktree` copy, add `traceback.extract_stack()[-7:-1]` and `v.tree`, `v.goal` to the line of `Gather.event`, play one game (`tools/play_check.py W --log F.jsonl`) and count the callers of the `idle` lines. One 20-minute game named `Bot.move` → `Bot.go` → `Gather.go` with `v.goal` None.
- The AoE2 wiki API gives `missingtitle` for a guessed page name (`Resources_(Age_of_Empires_II)`, `Game_setup`): find the name first with `action=query&list=search&srsearch=WORDS` (the Art of War page is `The Art of War (Age of Empires II)`, #3759).
- The server log has ANSI colors only when `TERM` (or `COLORTERM`) names a color terminal: Adventure (`net.kyori.ansi.ColorLevel`) reads them, and `-Dterminal.ansi=true` does not turn colors on. CI has no `TERM`, the cloud session has `TERM=linux`: a log test passed here and failed in CI. `game/run.py` sets `-Dnet.kyori.ansi.colorLevel=indexed16`; a regex of a log line with a name must allow `\x1b[..m` around it (`JOINED`, `play_guide.CHAT`, #3889).
- `civs.MISSING` has two sources (#1971, #2235): the `"missing"` list of each civilization line of `game/data/civs.jsonl` (most civs have the item), and the key `"civs"` of the item line in `game/data/train.jsonl` or `build.jsonl` (few civs have it: a unique or regional item).
- A new replay menu action in `replay_input.actions()` goes into the chat help line, and that line must stay under the RCON limit (1446 bytes): #3369 kept its action out of `actions()` (the poll loop lists it) and the `help_text` test failed for 14 tests.
- A bot that is slow in a `tools/play_check.py` game: read the stderr line of each game minute (`stock`, the villagers per task) before a fix. #4285 had two causes (soldiers took the food before `research`, and gold piled up to 1100), and the fix of the first cause alone changed nothing. A 30-minute game at `--speed 2` takes about 10 minutes: start the run on main in a `git worktree` first, and code while it runs.
- A fake live unit in a test of `train.research` (`g.soldiers[uuid] = NAME`) needs `server.entities[uuid] = {"Pos": (...)}` of the `FakeServer`: `train.census` drops a unit with no position, so the research sends it no command (#4283).
- A new field of `combat.Stats` with a default (`blast`, #4283): `tests/test_unit_data.py` and `tests/test_building_data.py` require each field of `Stats._fields` in each data line, so subtract the optional field there. Run `grep -ln "Stats._fields" tests/` with a change of `Stats`.
- A new optional field at the end of `aoe stats` (`combat.stats_command`, its list `tail`): a field that is not set prints its "off" value when a later field is set ("-", "0"). The `ignore` field of #4331 printed "1" always, so with a later field each unit ignored the armor (fixed in #4332). Change the parse in `AoePlugin.java` (`args.length` limit) too.
- A test that monkeypatches `train.BY_KEY` must patch both modules when other code imports `train` by its plain name (`import train` in `game/near.py`, `civs.regen`): `from game import train` is another module object with its own dict. Patch `train.BY_KEY` and `plain_train.BY_KEY` (`import train as plain_train`, as `tests/test_tech_effect_code.py`, #4333).
- In a `-m mc` test, a unit that takes a hit attacks back (the default stance, #733): it walks to the attacker, and the melee hits of the attacker add to the damage that the test counts. Give the target `movement_speed` 0 (`attribute ... base set 0`) when the test counts the hits of one attack (#4368: 4 hits in place of the 2 axes).
- A `monkeypatch` of a table of `game.combat` (`ON_DEATH`, `DODGE` ...) does not reach `train.py`, `spoils.py` or `scenario.py`: they read the bare `combat`. Patch both (`import combat as inner`, `keys()` of `tests/test_on_death.py`, #4471).
- The airef pages (AI script facts and actions) are made by JavaScript: WebFetch and curl get only the page frame. The texts are in `https://airef.github.io/js/commands.js` (`cX.description = "..."`, X the command in CamelCase): fetch it with curl to the scratchpad and grep it (#4740).
- In a live replay a joined player is in creative mode (force-gamemode), and the camera commands (`--camera`, `--follow`) act only on `@a[gamemode=spectator]`. A server check with `mc_shot.Client` must set spectator mode after the replay starts, from the replay thread (one RCON socket), for example in a wrapper of `game.batch` (#4770).
