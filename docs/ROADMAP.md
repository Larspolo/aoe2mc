# Roadmap

The project has three goals. This file lists the features of each goal: done (`[x]`) or missing (`[ ]`).
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
- [ ] `convert:triggers` Scenario triggers as datapack functions: messages, objectives, timers
- [ ] `convert:large` Large maps (480 × 480) in less time and memory, with a progress line
- [ ] `convert:minimap` A filled Minecraft map item of the whole AoE2 map at the spawn, as the AoE2 minimap

## 2. Play AoE2 in Minecraft (`game/`)

- [x] `play:program` A game program on a Paper server with Minecraft path finding (#433)
- [x] `play:gather` Gather wood, food, gold and stone, with drop sites and AoE2 work rates (#388)
- [x] `play:build` Place and build a construction site; a finished building works (#394)
- [ ] `play:fight` Military units fight: AoE2 attack, armor, range and hit points (epic #395)
- [ ] `play:train` Train villagers at the town center: cost, queue, population limit (epic #396)
- [ ] `play:bot` A scripted bot plays player 2 (epic #397)
- [ ] `play:scale` Measure and raise the number of units that the program can move (epic #398)
- [ ] `play:menu` Choose the options of a building and the build menu in a chest menu (epic #618, owner decision)
- [x] `play:health` Health indication: hit points over each unit and building, a boss bar for the selected unit, damage effects (#657)
- [ ] `play:military-train` Train all units at their buildings (barracks, archery range, stable, castle) with a queue and a rally point
- [ ] `play:tech` Technologies and upgrades (blacksmith, university, unit lines) with cost, time and effect on the Minecraft attributes
- [ ] `play:ages` Age up from the Dark Age to the Imperial Age: cost, time, the buildings and units that each age unlocks
- [x] `play:feedback` Show what the player points at and the result of each action (epic #793)
- [ ] `play:control` Select and order many units: a selection box, groups, formations, an idle villager item
- [ ] `play:garrison` Garrison units in buildings; the town center and castles shoot arrows
- [ ] `play:win` Win and lose: destroy all buildings, a wonder, relics; a title for the end of the game
- [ ] `play:monks` Monks heal and convert, relics in monasteries
- [ ] `play:market` Market trade and trade carts
- [ ] `play:two-players` Two human players against each other on one server
- [ ] `play:walls` Build walls and gates; a gate opens for own units and stays closed for enemies
- [ ] `play:siege` Siege units: rams against buildings, mangonels with area damage, trebuchets that pack and unpack
- [ ] `play:cheats` The AoE2 cheat codes in the chat when cheats are on (epic #820)

## 3. Replay a recorded game in Minecraft (`game/replay.py`, `aoe2mc.read_timeline`)

- [x] `replay:start` The start state of a record (#139) and its command timeline (#372)
- [x] `replay:live` A world at a time (`--at MM:SS`, #373) and a live replay: buildings, chat, ages, research (#374)
- [x] `replay:units` Trained units appear and walk to their targets with Minecraft path finding (#375, #408, #409, #410, #438)
- [x] `replay:versions` Records of other game versions (#376)
- [x] `replay:record` Replay a recorded game as fully as the file allows (epic #371)
- [ ] `replay:simulate` Simulate what the record does not contain with the rules of the game program: gathering, fights, deaths, destroyed buildings
- [ ] `replay:control` Control the replay in the game (today only `--speed` and `--from` at the start): pause, speed, jump to a time, a boss bar with the game time
- [ ] `replay:follow` The units of the live replay follow the record: positions, gathering, no stuck units (epic #814)
- [ ] `replay:view` A spectator view: follow a player or a unit, an overview from above
- [ ] `replay:score` A score panel for each player: age, population, resources (estimated), military
- [ ] `replay:effects` Show events on the map: research and age-up at the building, attacks, a marker where units die
- [ ] `replay:postgame` A summary at the end of the replay, as the AoE2 achievements screen: military, economy, technology, timeline

## Principles

1. One ticket = one PR. Split a large ticket (`size:L`) into sub-issues first.
2. The first sub-issue of an epic is small and useful alone.
3. Minecraft features first (CLAUDE.md): each epic names the Minecraft feature that does the job.
4. The owner decides the priorities. The agents propose changes in a comment.
