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

### Smallest playable milestone: "villagers gather wood"

1. The converter writes `aoe2mc.json` into the world folder: each object with its AoE2 ID, name, owner,
   tile position and the UUID of its entity.
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
- A new item of a building menu (`train.show()`) changes the exact menu strings in 5 test files (`grep -n "aoe menu Steve\|endswith(\"queue" tests/`): add it as a constant next to `FEUDAL` and `RALLY` in `tests/test_train_menu.py` (#672, #707).
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
