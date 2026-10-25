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
