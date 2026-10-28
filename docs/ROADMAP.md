# Roadmap

The project has three goals for the game and a fourth for the agent system that does the work. This file lists the features of each goal: done (`[x]`) or missing (`[ ]`).
The `roadmap` skill makes the next epic from a missing feature when the queue has no other work, and every 10th
run reviews this list (owner decisions, 2026-10-26: the agents make the epics themselves, at `P3`; the goals take
turns). The owner changes the priority of an epic or adds a feature here at any time.

Each feature has a key in backticks (`tools/release.py` and `docs/RELEASE.md` use it). An epic names its key in its body ("Roadmap: `play:health`"), so a run
can see which features have an epic: `gh api "repos/Larspolo/aoe2mc/issues?labels=epic&state=all&per_page=100"`.

## 1. Convert maps to Minecraft (`aoe2mc.py`, `buildings.py`, `units.py`)

- [x] `convert:terrain` Terrain, elevation, cliffs, water at its height with natural shores (#155)
- [x] `convert:designs` A recognizable form for each building, unit, hero and object (#42, #41, #22), furniture inside (#186)
- [x] `convert:units` Units with facing and garrisons, walls and gates, ships with passengers
- [x] `convert:inputs` Campaigns (#149), old `.scx` scenarios (#310, #313), recorded games at a time (#373)
- [x] `convert:version` Minecraft Java 26.3 only (#14, #426); example worlds and a gallery (#181)
- [x] `convert:texts` The scenario texts in a book at the spawn (#27); one team per player in the player color (#358)
- [x] `convert:sounds` Sounds and ambient effects in the world (#188)
- [x] `convert:triggers` Scenario triggers as datapack functions: messages, objectives, timers (epic #645)
- [x] `convert:large` Large maps (480 × 480) in less time and memory, with a progress line (epic #689)
- [x] `convert:minimap` A filled Minecraft map item of the whole AoE2 map at the spawn, as the AoE2 minimap (epic #837)
- [x] `convert:random-maps` Make a world from an AoE2 random map script (`.rms`: Arabia, Arena, Black Forest) and a seed, with no scenario file (epic #959)
- [x] `convert:random-maps-more` More random map scripts of the ranked pool and the classic ones (Nomad, Islands, Gold Rush, Highland, Mediterranean) with their player starts (epic #1172)
- [x] `convert:mood` The map color mood and weather of a DE scenario (`map_color_mood`: morning, noon, evening, night, snow, fog) as the Minecraft time of day, weather and fog (epic #1593)
- [ ] `convert:start-view` The start view of each scenario player (`initial_camera_x`, `initial_camera_y` of the scenario): the Minecraft spawn at the view of player 1, and in the game program each side starts at the view of its player

## 2. Play AoE2 in Minecraft (`game/`)

- [x] `play:program` A game program on a Paper server with Minecraft path finding (#433)
- [x] `play:gather` Gather wood, food, gold and stone, with drop sites and AoE2 work rates (#388)
- [x] `play:build` Place and build a construction site; a finished building works (#394)
- [x] `play:fight` Military units fight: AoE2 attack, armor, range and hit points (epic #395)
- [x] `play:train` Train villagers at the town center: cost, queue, population limit (epic #396)
- [x] `play:bot` A scripted bot plays player 2 (epic #397)
- [x] `play:scale` Measure and raise the number of units that the program can move (epic #398)
- [x] `play:menu` Choose the options of a building and the build menu in a chest menu (epic #618, owner decision)
- [x] `play:health` Health indication: hit points over each unit and building, a boss bar for the selected unit, damage effects (#657)
- [x] `play:military-train` Train all units at their buildings (barracks, archery range, stable, castle) with a queue and a rally point (epic #704)
- [x] `play:tech` Technologies and upgrades (blacksmith, university, unit lines) with cost, time and effect on the Minecraft attributes (epic #936)
- [x] `play:ages` Age up from the Dark Age to the Imperial Age: cost, time, the buildings and units that each age unlocks (epic #1079)
- [x] `play:civs` Civilizations: the bonuses, unique technologies and team bonus of each civilization change costs and attributes (epic #1088)
- [x] `play:feedback` Show what the player points at and the result of each action (epic #793)
- [x] `play:alerts` Alerts as in AoE2: a sound and a chat line with the place when own units or buildings are attacked, and a flare that a player puts on the map (epic #1230)
- [x] `play:control` Select and order many units: a selection box, groups, formations, an idle villager item (epic #742)
- [x] `play:stances` Unit stances (aggressive, defensive, stand ground, no attack): an idle unit attacks the enemies in its line of sight and comes back (epic #1103)
- [x] `play:garrison` Garrison units in buildings (epic #810)
- [x] `play:arrows` The town center, towers and castles shoot arrows at enemies in range, more arrows with a garrison (epic #1110)
- [x] `play:win` Win and lose: destroy all buildings, a wonder, relics; a title for the end of the game (epic #1134)
- [x] `play:monks` Monks heal and convert, relics in monasteries (epic #1242)
- [x] `play:market` Market trade and trade carts (epic #1250)
- [x] `play:two-players` Two human players against each other on one server (epic #1306)
- [x] `play:diplomacy` Teams and diplomacy: allied, neutral and enemy players, shared line of sight, tribute of resources (epic #1311)
- [x] `play:walls` Build walls and gates; a gate opens for own units and stays closed for enemies (epic #1321)
- [x] `play:repair` Villagers repair damaged buildings and siege units for a part of the cost; a damaged building shows fire (epic #1329)
- [x] `play:siege` Siege units: rams against buildings, mangonels with area damage, trebuchets that pack and unpack (epic #1348)
- [x] `play:naval` Docks and ships: fishing ships and fish traps gather food, warships fight on water, transport ships carry units (Minecraft boats) (epic #1381)
- [x] `play:cheats` The AoE2 cheat codes in the chat when cheats are on (epic #820)
- [x] `play:fog` The explored area and the fog of war: a player sees only what the own units and buildings see (epic #1387)
- [x] `play:save` Save a game of the game program and load it again (units, resources, queues, ages) (epic #2253)
- [x] `play:hunt` Hunt and herd: villagers kill deer, lure and kill boars, and herd sheep that the first player who sees them owns (#1058, `game/herd.py`, #2310)
- [ ] `play:setup` Set up a game before it starts: the starting age, starting resources, population limit, the civilizations and the number of bots
- [ ] `play:scenario` Play a converted scenario in the game program: its objectives, triggers and victory conditions work, the scenario AI players are bots
- [x] `play:minimap` A minimap as in AoE2: a held Minecraft map item that shows the own and the seen enemy units and buildings as markers in the player colors, and a click on it sends the selection there (epic #2580)
- [ ] `play:spectate` Spectators on the server of a game: they fly and see all players, without a side, as the AoE2 spectator mode
- [ ] `play:unit-commands` The other AoE2 orders: patrol between points, guard a unit or building, follow a unit, attack-move (attack each enemy on the way)
- [ ] `play:speed` Pause and game speed of the game program, as the AoE2 pause key and the speed setting: the units, queues and gathering stop and go on
- [x] `play:postgame` The statistics at the end of a game of the game program, as the AoE2 achievements screen: military, economy, technology, the time of each age (the recap book, #2660, #2706)
- [x] `play:taunts` AoE2 taunts: a player types a taunt number (1-105) in the chat, and all players hear its sound and see its text (#3318)
- [ ] `play:wildlife` Wild predators as in AoE2: wolves, tigers and other predators of the map attack villagers and units near them
- [x] `play:farm-reseed` Farm reseeds as in AoE2: the mill queues farms, and an exhausted farm is built again by its farmer when the player has the wood (#3283)
- [x] `play:game-modes` The AoE2 game modes in the game setup: Regicide (a king per player), Death Match (large start resources), King of the Hill (hold the monument) and Empire Wars (a running start economy) (#2387, #2452, #2383, #2428)
- [ ] `play:formations` AoE2 formations for a selected group (line, box, staggered, flank): the units keep their places on the walk, and the slowest unit sets the speed
- [ ] `play:town-bell` The town bell as in AoE2: a click at the town center sends the villagers into the nearest own buildings, a second click lets them out
- [ ] `play:delete` Delete an own unit or building as the AoE2 Delete key: the unit dies, the building falls down
- [x] `play:auto-gather` Villagers go on to work as in AoE2: a villager that builds a lumber camp, mining camp or mill gathers the nearest resource of that kind next, and the builder of a farm farms it (#3271)
- [ ] `play:co-op` Co-op as in AoE2: two or more Minecraft players control one AoE2 player (one civilization, one stock and population), each with an own selection
- [ ] `play:unit-sounds` The AoE2 sounds of the units and buildings: a voice line when the player selects a unit and gives an order, the sound of a selected building, the age-up fanfare
- [ ] `play:campaign` Play a campaign in the game program: its scenarios in order, the next scenario after a victory, the intro and history texts of each scenario
- [ ] `play:waypoints` Queued orders as in AoE2 (a shift click): a selected group walks to several points in a row, and a villager builds several construction sites one after the other
- [ ] `play:auto-queue` The AoE2 DE auto-queue: a building trains one unit again and again while the player has the resources and the population, until the player stops it
- [ ] `play:tech-tree` The AoE2 tech tree screen: the units, buildings and technologies of the own civilization by age and building, and the ones that the civilization does not have
- [ ] `play:team-chat` The AoE2 chat targets: a chat line to all players, to the allies only or to one player, in the player color (Minecraft `/teammsg` and `/msg`)

## 3. Replay a recorded game in Minecraft (`game/replay.py`, `aoe2mc.read_timeline`)

- [x] `replay:start` The start state of a record (#139) and its command timeline (#372)
- [x] `replay:live` A world at a time (`--at MM:SS`, #373) and a live replay: buildings, chat, ages, research (#374)
- [x] `replay:units` Trained units appear and walk to their targets with Minecraft path finding (#375, #408, #409, #410, #438)
- [x] `replay:versions` Records of other game versions (#376)
- [x] `replay:record` Replay a recorded game as fully as the file allows (epic #371)
- [x] `replay:simulate` Simulate what the record does not contain with the rules of the game program: gathering, fights, deaths, destroyed buildings (epic #629)
- [x] `replay:control` Control the replay in the game: pause, speed, jump to a time, a boss bar with the game time (epic #683)
- [x] `replay:follow` The units of the live replay follow the record: positions, gathering, no stuck units (epic #814)
- [x] `replay:view` A spectator view: follow a player or a unit, an overview from above (epic #736)
- [x] `replay:score` A score panel for each player: age, population, resources (estimated), military (epic #740)
- [x] `replay:effects` Show events on the map: research and age-up at the building, attacks, a marker where units die (epic #842)
- [x] `replay:postgame` A summary at the end of the replay, as the AoE2 achievements screen: military, economy, technology, timeline (epic #1064)
- [x] `replay:team-games` Team games of up to 8 players: the score panel, the colors, the views and the summary work with all players (epic #1187)
- [x] `replay:minimap` A live minimap of the replay: a Minecraft map item that shows the units and buildings of all players in their colors and changes with the game (epic #1236)
- [x] `replay:fog` The view of one player in the replay: only what the units and buildings of that player see, as the AoE2 "line of sight" option of the replay (epic #1299)
- [x] `replay:taunts` The taunts of the record (a chat line with a number) play their sound and show their text in the live replay (epic #2232)
- [x] `replay:flares` The flares of the record (a player marks a place for the allies) show at their place in the live replay: a beacon light and a chat line in the player color (epic #2401)
- [x] `replay:orders` The other orders of the record change the units of the live replay: stances, formations, patrol and the town bell (epic #2547)
- [ ] `replay:production` A production panel of each player in the live replay, as the AoE2 DE replay overlay: the units in training and the technologies in research, with their progress
- [ ] `replay:highlights` A list of the large fights of the record (where and when many units die): a jump to the time and the place of each fight
- [ ] `replay:auto-camera` An automatic camera of the live replay, as a caster view: the spectator view moves by itself to the place with the most fights or the most new buildings
- [ ] `replay:graphs` Live graphs of the replay, as the statistics of the AoE2 DE replay overlay: the military, the economy and the population of each player over the game time

## 4. The agent system (`.claude/skills/`, `tools/`, `.github/workflows/`)

Owner (2026-10-26): "reach the final goals efficiently while keeping up the quality and leaving behind a system to do
other projects with". The `roadmap` skill makes no epics for this goal: the `improve` skill and the owner do.

- [ ] `system:improve` The system improves itself in its own loop, over the whole system, and only where it pays (epic #908)
- [x] `system:reuse` The system can be set up for another project (epic #909)
- [x] `system:structure` The code stays easy to change: game data in data files, checks in place of rules (epic #1909)

## Principles

1. One ticket = one PR. Split a large ticket (`size:L`) into sub-issues first.
2. The first sub-issue of an epic is small and useful alone.
3. Minecraft features first (CLAUDE.md): each epic names the Minecraft feature that does the job.
4. The owner decides the priorities. The agents propose changes in a comment.
