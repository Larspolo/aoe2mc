# Play test: start, join and report a bug

Use this page to play a test game of aoe2mc and to report a bug. You do not need to know the project (#3326).

## 1. Install

1. Install Python 3.10 or newer, then get the repository and its packages:

       git clone https://github.com/Larspolo/aoe2mc
       cd aoe2mc
       python3 -m pip install -r requirements.txt

   The installers of the release also work (`README.md`, "Install"). Then use `aoe2mc-game` in place of
   `python3 game/run.py`.
2. Install Java 25 (for example Temurin 25 from adoptium.net). The game program builds a small server plugin, so
   it needs the JDK (with `javac`), not only the JRE.
3. Install Minecraft Java Edition 26.3 in the Minecraft launcher.

## 2. Make a world

    python3 tools/scenarios.py owner_loop OUT.aoe2scenario
    python3 aoe2mc.py OUT.aoe2scenario OUTWorld

The first command makes a small test map with two players. The second command converts it into the Minecraft
world `OUTWorld`. You can also convert your own `.aoe2scenario` file.

## 3. Start and join

Start with the tutorial. It shows each step in the boss bar and the chat (select a villager, gather wood, build a
house). After the last step, stop the game with Ctrl-C and start the bot game below. The installer path uses
`aoe2mc-game` in place of `python3 game/run.py`.

    python3 game/run.py OUTWorld --play --tutorial

Then start the bot game:

    python3 game/run.py OUTWorld --play --bot

The first start downloads the Minecraft server (about 1 minute). When the console shows
"Join the server localhost:PORT", start Minecraft 26.3, click "Multiplayer", "Direct Connection" and type that
address. You play player 1; the bot plays player 2 and attacks you. Ctrl-C in the console stops the game.

Add `--cheats` to use the AoE2 cheat codes in the chat (for example `aegis`: fast building and training).

## 4. Controls

Hold the carrot on a stick. The action bar at the bottom of the screen always shows the next possible step. The
tutorial (section 3) teaches the same controls.

- Select: right click a unit. Hold right click and look across the ground: a selection box.
- Move: with a selection, right click the ground.
- Gather: select villagers, then right click a tree, a fruit bush, a mine or a farm.
- Build: select villagers, right click them for the build menu, select a building, then right click the ground.
- Train: right click your own building (town center, barracks ...) and click a unit in its menu.
- Attack: select military units, then right click an enemy.

The sidebar shows your wood, food, gold and stone.

## 5. Report a bug

Make an issue in [Larspolo/aoe2mc](https://github.com/Larspolo/aoe2mc/issues/new) with:

- the steps that cause the bug, and what you expected,
- the game time (the minutes since the start of the game),
- a screenshot (F2 in Minecraft),
- the server log: copy `.cache/<newest folder>/logs/latest.log` before you stop the game (the game program deletes
  the server folder when it stops), and the text of the console.
