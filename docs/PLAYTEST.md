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
house). After the last step, stop the game with Ctrl-C and start the bot game. A game changes its world, so make
a new world for the bot game (here `BotWorld`, as in section 2).

With the installer:

    aoe2mc-game OUTWorld --play --tutorial
    aoe2mc --random-map arabia --seed 1 BotWorld
    aoe2mc-game BotWorld --play --bot --ai-difficulty easiest

With Python:

    python3 game/run.py OUTWorld --play --tutorial
    python3 aoe2mc.py OUT.aoe2scenario BotWorld
    python3 game/run.py BotWorld --play --bot --ai-difficulty easiest

For a stronger bot, use `--ai-difficulty standard`, `moderate`, `hard`, `hardest` or `extreme`.

To play with more people, add `--people N` (with `--bot`, the bot plays player N + 1). Each person joins the same
address, opens the Game menu (section 4), clicks "Choose your player" and then "Ready". The game starts when all
people are ready.

The first start downloads the Minecraft server (about 1 minute). When the console shows
"Join the server localhost:PORT", start Minecraft 26.3, click "Multiplayer", "Direct Connection" and type that
address. The game clock starts when you joined ("The game starts when 1 person joined"). You play player 1; the
bot plays player 2 and attacks you. Ctrl-C in the console stops the game and saves it: the console shows the
command to continue (`--load`). With the installer, use `aoe2mc-game` in place of `python3 game/run.py`
in that command.

Add `--cheats` to use the AoE2 cheat codes in the chat (for example `aegis`: fast building and training).
With `--cheats`, the Minecraft command `/give @s gold` (also `food`, `wood`, `stone`) gives the resource as the
cheat codes do (for example `robin hood`: 10000 gold).

### Play with friends

One computer is the host: it runs the game program and the Minecraft server. Each friend needs only Minecraft Java
Edition 26.3 and a Minecraft account, not the game program.

The host:

1. Make a world (section 2). With Python, convert with the resource pack: the friends need it.

       python3 aoe2mc.py OUT.aoe2scenario OUTWorld --resource-pack

2. Start the game with `--host`, `--invite` and `--people`. `--invite` gives the Minecraft names that can join:
   write your own name too, else the program stops. `--people` gives the number of people, you included. For you
   (Alex) and two friends:

       aoe2mc-game OUTWorld --play --host --invite Alex,Sam,Robin --people 3

   With Python:

       python3 game/run.py OUTWorld --play --host --invite Alex,Sam,Robin --people 3

   You can add `--bot` or `--bots` as in section 3.
3. The firewall of your computer must let the game port and the port of the resource pack in. Windows asks at the
   first start: click "Allow" for Java and for the game program (with Python: for Python).
4. The console shows two lines. "Join the server localhost:PORT" is for you. "Join the server ADDRESS:PORT (other
   computers on the network)." is for your friends: send them ADDRESS:PORT. To invite one more friend while the
   game runs, type `whitelist add NAME` in the console (NAME: the Minecraft name of the friend).
5. The program selects a free port at each start, also with `--load` (not with `--port N`). After each start,
   send the new address.
6. Join on localhost:PORT as in section 3. The page "Choose your player" opens: select your AoE2 player and click
   "Ready".

A friend:

1. Install Minecraft Java Edition 26.3 in the Minecraft launcher.
2. Start Minecraft 26.3, click "Multiplayer", "Direct Connection" and type the address of the host.
3. Accept the resource pack: the units need it. The server sends the pack only when the world has one
   (host step 1). If you do not accept it, the server disconnects you.
4. The page "Choose your player" opens: select your AoE2 player and click "Ready". The game starts when all people
   are ready.
5. If the server says "You are not whitelisted on this server!", tell the host your exact Minecraft name. The host types
   `whitelist add NAME` in the console of the game program (no restart). Then join again.

A network with no internet: the host adds `--offline`. Then Minecraft does not check the login of the players, but
the white-list still checks the names. The console shows "Warning: --offline: no Minecraft login check, a stranger
can join with an invited name". Use `--offline` only on a network that you trust.

Over the internet, ADDRESS is an address of the local network only. Do one of these steps:

- Forward two fixed ports in the router of the host to the ADDRESS of the line: add `--port N` (the game port, TCP)
  and forward N and N+1 (N+1 is the port of the resource pack). Add `--address` with the public address of the
  router. The friends type that address and the port N.
- Use a VPN for games: it puts the computers on one virtual network. Add `--address` with the VPN address of the
  host. The friends type the VPN address and the PORT. This project has no VPN tool.

For example: `python3 game/run.py OUTWorld --play --host --invite Alex,Sam --address 203.0.113.7 --port 25600`.
The resource pack URL uses the address of `--address`, so the friends can download the pack. With the installer, the
friends download the resource pack from GitHub.

### Make a map with the editor

1. Make a world (step 2), then start the editor: `python3 game/run.py MyWorld --editor MyMap.aoe2scenario`.
   The game time does not start. You are in creative mode. Or start on a new empty map with `--new SIZE` (a new
   world folder), with `--terrain NAME` (the base terrain, default GRASS_1) and `--players N` (1 to 8, default 2):
   `python3 game/run.py NewWorld --editor MyMap.aoe2scenario --new 120 --terrain DESERT_SAND --players 4`.
2. Paint the terrain with blocks of the creative inventory: the top block of a tile gives its AoE2 terrain. For water,
   put sand (shallow) or gravel (deep) under the water. Add or remove 3 blocks of height to change the elevation of a
   tile by one level.
3. Type `palette` in the chat to open the palette: tabs Units, Buildings, Resources, Cliffs, Heroes and Gaia (relics,
   rocks, ruins and decor). Right-click an object to put it where you look. For a wall line, right-click a wall at the
   start and again at the end: the editor puts a segment on each tile between them. Type `palette <word>` (for
   example `palette relic`) to see only the objects of all tabs with that word in the name.
4. Look at an object and type `remove` in the chat to remove it.
5. Type `players` in the chat to open the players menu: select the current player (the owner of the next object), the
   civilization, the start resources and the starting age. Click the team item (white wool) to give the current player
   the next team (1 to 4, or none). Click the victory item (gold block) to select the next victory condition.
6. Type `messages` in the chat to get a book and quill for each scenario text (instructions, hints, victory, loss,
   history, scouts). Write the text in the book. Keep the books in your inventory until you save.
7. Type `options` in the chat to open the options menu: tabs Technologies, Buildings and Units. Click an item to
   disable it for the current player, click it again to enable it. Click the last item to select the next color mood
   of the map.
8. Type `save` in the chat. The editor writes `MyMap.aoe2scenario`. Stop the server (Ctrl-C) to save it one more time.
   Convert the map as in step 2, or open it in AoE2 DE.

## 4. Controls

Hold the carrot on a stick. The action bar at the bottom of the screen always shows the next possible step. The
tutorial (section 3) teaches the same controls. Type /controls in the game to see this list.

- Select: left click a unit. Hold left click and look across the ground: a selection box. Right click: give orders.
- Move: with a selection, right click the ground.
- Gather: select villagers, then right click a tree, a fruit bush, a mine or a farm.
- Build: select villagers, right click them for the build menu, select a building, then left click the ground.
  Shift + left click: place more. Right click: cancel.
- Train: right click your own building (town center, barracks ...) and click a unit in its menu.
- Attack: select military units, then right click an enemy.
- Research and age up: right click your own building and click a technology or the next age in its menu.
- Garrison: select units, then right click your own building. Its menu lets them out. Town center menu: Ring Town Bell.
- Camera: right click with the spyglass "Camera" (hotbar key 2). You walk fast on an invisible floor high above the
  map, and you can give orders from there. Shift right click: the next speed (5, 10 or 20 times the walk speed). Right
  click again: you fly down near the ground. Two client options help with the fast camera, both in Options >
  Accessibility Settings: "View Bobbing" OFF keeps the held item still while you walk. "FOV Effects" shows a wider
  view, which shows more of the map; set it to 0 % to keep the normal view.
- Go to: right click with the compass "Go to" (hotbar key 3): a menu of your town centers, your control groups and the next idle villager.
- Game menu: right click with the book "Game menu" (hotbar key 4): diplomacy and tribute, flare, save, pause and the tech tree.
  Two switches: "Unique Player Colors" off shows you in blue, your allies in yellow and your enemies in red.
  "Highlight huntable animals" makes the deer, boars and sheep glow for you.
- Control groups: select units, take a group item (hotbar keys 5 to 9) and Shift + right click to save the selection. Right click: select the group.

The sidebar shows your wood, food, gold and stone.

Language: the texts of aoe2mc (the action bar, the menus, the hints, the tutorial) use the language of your Minecraft client (Options > Language). The names of units, buildings and technologies stay English.

## 5. Report a bug

Make an issue in [Larspolo/aoe2mc](https://github.com/Larspolo/aoe2mc/issues/new) with:

- the steps that cause the bug, and what you expected,
- the game time (the minutes since the start of the game),
- the language of your Minecraft client (Options > Language), when a text is wrong or not clear,
- a screenshot (F2 in Minecraft),
- the server log: attach the file `last-game.log` that the game program writes when it stops (its path is printed
  as "Server log: ..."; the game program keeps it also after a crash or Ctrl-C), and the text of the console.
