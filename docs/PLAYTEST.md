# Play test: start, join and report a bug

Use this page to play a test game of aoe2mc and to report a bug. You do not need to know the project (#3326).

## 1. Install

There are two paths: the installer of the release (no Python, no repository) or Python.

1. Installer: download and start the installer of your system as README "Install", "Installer"
   (https://github.com/Larspolo/aoe2mc#install) tells. It gives two commands: `aoe2mc` (the converter) and
   `aoe2mc-game` (the game program). On Windows they are `aoe2mc.exe` and `aoe2mc-game.exe` in the install folder;
   on macOS they are in `/Applications/aoe2mc.app/Contents/MacOS/`.

   Python: install Python 3.10 or newer, then get the repository and its packages:

       git clone https://github.com/Larspolo/aoe2mc
       cd aoe2mc
       python3 -m pip install -r requirements.txt

2. Install Java 25 (for example Temurin 25 from adoptium.net). The game program builds a small server plugin, so
   it needs the JDK (with `javac`), not only the JRE.
3. Install Minecraft Java Edition 26.3 in the Minecraft launcher.

## 2. Make a world

With the installer:

    aoe2mc --random-map arabia --seed 1 OUTWorld

This command makes a random Arabia map with two players in the Minecraft world `OUTWorld`. The release also
attaches example worlds: unzip one and use its folder in place of `OUTWorld`.

With Python:

    python3 tools/scenarios.py owner_loop OUT.aoe2scenario
    python3 aoe2mc.py OUT.aoe2scenario OUTWorld

The first command makes a small test map with two players. The second command converts it into the Minecraft
world `OUTWorld`. You can also convert your own `.aoe2scenario` file.

## 3. Start and join

Start with the tutorial. It shows each step in the boss bar and the chat (select a villager, gather wood, build a
house). After the last step, stop the game with Ctrl-C and start the bot game.

With the installer:

    aoe2mc-game OUTWorld --play --tutorial
    aoe2mc-game OUTWorld --play --bot

With Python:

    python3 game/run.py OUTWorld --play --tutorial
    python3 game/run.py OUTWorld --play --bot

The first start downloads the Minecraft server (about 1 minute). When the console shows
"Join the server localhost:PORT", start Minecraft 26.3, click "Multiplayer", "Direct Connection" and type that
address. The game clock starts when you joined ("The game starts when 1 person joined"). You play player 1; the
bot plays player 2 and attacks you. Ctrl-C in the console stops the game and saves it: the console shows the
command to continue (`--load`). With the installer, use `aoe2mc-game` in place of `python3 game/run.py`
in that command.

Add `--cheats` to use the AoE2 cheat codes in the chat (for example `aegis`: fast building and training).

## 4. Controls

Hold the carrot on a stick. The action bar at the bottom of the screen always shows the next possible step. The
tutorial (section 3) teaches the same controls. Type /controls in the game to see this list.

- Select: right click a unit. Hold right click and look across the ground: a selection box.
- Move: with a selection, right click the ground.
- Gather: select villagers, then right click a tree, a fruit bush, a mine or a farm.
- Build: select villagers, right click them for the build menu, select a building, then left click the ground.
  Shift + left click: place more. Right click: cancel.
- Train: right click your own building (town center, barracks ...) and click a unit in its menu.
- Attack: select military units, then right click an enemy.
- Camera: right click with the spyglass "Camera" (hotbar key 2). You walk fast on an invisible floor high above the
  map, and you can give orders from there. Shift right click: the next speed (5, 10 or 20 times the walk speed). Right
  click again: you fly down near the ground. Two client options help with the fast camera, both in Options >
  Accessibility Settings: "View Bobbing" OFF keeps the held item still while you walk. "FOV Effects" shows a wider
  view, which shows more of the map; set it to 0 % to keep the normal view.

The sidebar shows your wood, food, gold and stone.

## 5. Report a bug

Make an issue in [Larspolo/aoe2mc](https://github.com/Larspolo/aoe2mc/issues/new) with:

- the steps that cause the bug, and what you expected,
- the game time (the minutes since the start of the game),
- a screenshot (F2 in Minecraft),
- the server log: attach the file `last-game.log` that the game program writes when it stops (its path is printed
  as "Server log: ..."; the game program keeps it also after a crash or Ctrl-C), and the text of the console.
