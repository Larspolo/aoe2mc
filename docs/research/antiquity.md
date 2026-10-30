# Research: the rules and the data of Antiquity Mode (#3665)

Part of epic #3664 (play Antiquity Mode, the Return of Rome mode of AoE2 DE). This document lists the Return of Rome
rules from the AoE wiki and plans the data structure of a second rule set in the game program. The next sub-issues
(#3666 to #3669 and the steps of section 4) use it.

Source: the AoE wiki (`ageofempires.fandom.com`), read with the MediaWiki API (`action=parse`,
`prop=wikitext`; the HTML is blocked), 2026-10-29. `python3 tools/refimage.py box PAGE...` prints the infobox values of each page (cost, age, hit points,
attack, upgrade cost) as one JSON line: the later steps read their values with it. The URL of a page is
`https://ageofempires.fandom.com/wiki/` + the page name with `_` for each space. All 140 page names in the tables
below exist (API `action=query`, 2026-10-29). The values are those of the infobox of each page (Return of Rome).

## 1. The Return of Rome rules

The mode is separate in AoE2 DE: "the content in that game mode cannot be played with Age of Empires II content"
(page "Age of Empires II: Definitive Edition - Return of Rome"). So a game uses one rule set from start to end.

### 1.1 Civilizations (17)

Page "Civilization (Age of Empires)". The bonuses, the team bonus, the missing units and the missing technologies
are in the section "Characteristics" of the page of each civilization.

| Civilization | Wiki page | Architecture | Focus |
|---|---|---|---|
| Assyrians | Assyrians | Egyptian | archers, siege |
| Babylonians | Babylonians | Mesopotamian | defense |
| Carthaginians | Carthaginians | Roman | elephants, camels, navy |
| Choson | Choson | East Asian | infantry, towers |
| Egyptians | Egyptians (Age of Empires) | Egyptian | chariots, priests |
| Greeks | Greeks (Age of Empires) | Greek | infantry, navy |
| Hittites | Hittites | Egyptian | archers, siege |
| Lac Viet | Lac Viet | East Asian | archers |
| Macedonians | Macedonians (Age of Empires) | Roman | infantry |
| Minoans | Minoans | Greek | archers, navy |
| Palmyrans | Palmyrans | Roman | camels, trade |
| Persians | Persians (Age of Empires) | Mesopotamian | elephants, navy |
| Phoenicians | Phoenicians | Greek | elephants, navy |
| Romans | Romans (Age of Empires) | Roman | infantry |
| Shang | Shang | East Asian | economy, cavalry |
| Sumerians | Sumerians | Mesopotamian | economy, siege |
| Yamato | Yamato | East Asian | cavalry, navy |

### 1.2 Ages (4)

The town center researches each age. A player needs two buildings of the current age (any two of the list, not the
town center and not houses).

| Age | Wiki page | Cost | Time | Required buildings (two of them) |
|---|---|---|---|---|
| Stone Age | Stone Age | (start) | | |
| Tool Age | Tool Age | 500 food | 120 s | Barracks, Dock, Granary, Storage Pit |
| Bronze Age | Bronze Age | 800 food | 140 s | Archery Range, Market, Stable |
| Iron Age | Iron Age | 1000 food, 800 gold | 160 s | Academy, Government Center, Siege Workshop, Temple |

Greeks advance to the Bronze Age and the Iron Age 10 % faster (the pages of the two ages).

### 1.3 Buildings

Page "Building (Age of Empires)". "Unlocks": the building must stand before a player can build the other buildings.

| Building | Wiki page | Age | Cost | Time | Unlocks |
|---|---|---|---|---|---|
| Town Center | Town Center (Age of Empires) | Stone (one); Bronze (more, after a Government Center) | 200 wood | 60 s | |
| House | House (Age of Empires) | Stone | 30 wood | 20 s | |
| Barracks | Barracks (Age of Empires) | Stone | 125 wood | 30 s | Archery Range, Stable |
| Granary | Granary (Age of Empires) | Stone | 120 wood | 30 s | Market |
| Storage Pit | Storage Pit (Age of Empires) | Stone | 120 wood | 30 s | |
| Dock | Dock (Age of Empires) | Stone | 100 wood | 50 s | |
| Archery Range | Archery Range (Age of Empires) | Tool | 150 wood | 40 s | Siege Workshop |
| Stable | Stable (Age of Empires) | Tool | 150 wood | 40 s | Academy |
| Market | Market (Age of Empires) | Tool | 150 wood | 40 s | Farm, Government Center, Temple |
| Farm | Farm (Age of Empires) | Tool | 75 wood | 24 s | |
| Small Wall | Small Wall | Tool | 5 stone | 7 s | |
| Small Gate | Small Gate | Tool | 30 stone | 35 s | |
| Watch Tower | Watch Tower (Age of Empires) | Tool | 150 stone | 65 s | |
| Government Center | Government Center | Bronze | 175 wood | 60 s | Town Center |
| Temple | Temple (Age of Empires) | Bronze | 200 wood | 60 s | |
| Siege Workshop | Siege Workshop (Age of Empires) | Bronze | 200 wood | 60 s | |
| Academy | Academy (Age of Empires) | Bronze | 150 wood | 60 s | |
| Medium Wall | Medium Wall | Bronze | 5 stone | 7 s | |
| Medium Gate | Medium Gate | Bronze | 30 stone | 35 s | |
| Sentry Tower | Sentry Tower (Age of Empires) | Bronze | 150 stone | 65 s | |
| Wonder | Wonder (Age of Empires) | Iron | 1000 wood, 1000 stone, 1000 gold | 3500 s | |
| Fortified Wall | Fortified Wall (Age of Empires) | Iron | 5 stone | 7 s | |
| Fortified Gate | Fortified Gate (Age of Empires) | Iron | 30 stone | 35 s | |
| Guard Tower | Guard Tower (Age of Empires) | Iron | 150 stone | 65 s | |
| Ballista Tower | Ballista Tower (Age of Empires) | Iron (after Ballistics) | 150 stone | 65 s | |

Drop sites (page "Storage Pit (Age of Empires)"): the Granary takes the food of farms and berry bushes; the Storage
Pit takes wood, stone, gold and the food of hunt and fish; the town center takes all. A wall, gate or tower of a
later age replaces the one of the earlier age by a research at the Granary (section 1.5). Army Tent and Barricade
(pages "Army Tent (Age of Empires)", "Barricade (Age of Empires)") have no age and no cost in their infobox: they
are not in the build menu of a standard game.

### 1.4 Units

Page "Unit (Age of Empires)". "→" is an upgrade: the building researches it, at the cost of the page of the earlier
unit ("UpCost").

| Unit line | Wiki pages | Building | Age of each unit | Cost of the first unit |
|---|---|---|---|---|
| Villager | Villager (Age of Empires) | Town Center | Stone | 50 food |
| Clubman → Axeman | Clubman, Axeman (Age of Empires) | Barracks | Stone, Tool | 50 food |
| Short Swordsman → Broad Swordsman → Long Swordsman → Legionary | Short Swordsman, Broad Swordsman, Long Swordsman (Age of Empires), Legionary (Age of Empires) | Barracks | Bronze, Bronze, Iron, Iron | 35 food, 15 gold |
| Slinger | Slinger (Age of Empires) | Barracks | Tool | 40 food, 10 stone |
| Bowman | Bowman (Age of Empires) | Archery Range | Tool | 40 food, 20 wood |
| Improved Bowman → Composite Bowman | Improved Bowman, Composite Bowman (Age of Empires) | Archery Range | Bronze, Bronze | 40 food, 20 gold |
| Chariot Archer | Chariot Archer (Age of Empires) | Archery Range | Bronze | 40 food, 70 wood |
| Horse Archer → Heavy Horse Archer | Horse Archer (Age of Empires), Heavy Horse Archer | Archery Range | Iron, Iron | 50 food, 70 gold |
| Elephant Archer | Elephant Archer (Age of Empires) | Archery Range | Iron | 180 food, 60 gold |
| Scout | Scout (Age of Empires) | Stable | Tool | 90 food |
| Chariot → Scythe Chariot | Chariot (Age of Empires), Scythe Chariot | Stable | Bronze, Iron | 40 food, 60 wood |
| Cavalry → Heavy Cavalry → Cataphract | Cavalry (Age of Empires), Heavy Cavalry (Age of Empires), Cataphract (Age of Empires) | Stable | Bronze, Iron, Iron | 70 food, 80 gold |
| War Elephant → Armored Elephant | War Elephant (Age of Empires), Armored Elephant (Age of Empires) | Stable | Iron, Iron | 170 food, 40 gold |
| Camel Rider | Camel Rider (Age of Empires) | Stable | Bronze | 70 food, 60 gold |
| Stone Thrower → Catapult → Heavy Catapult | Stone Thrower, Catapult (Age of Empires), Heavy Catapult | Siege Workshop | Bronze, Iron, Iron | 180 wood, 80 gold |
| Ballista → Helepolis | Ballista (Age of Empires), Helepolis (Age of Empires) | Siege Workshop | Iron, Iron | 100 wood, 80 gold |
| Hoplite → Phalangite → Centurion | Hoplite (Age of Empires), Phalangite (Age of Empires), Centurion (Age of Empires) | Academy | Bronze, Iron, Iron | 60 food, 40 gold |
| Priest | Priest (Age of Empires) | Temple | Bronze | 125 gold |
| Fishing Boat → Fishing Ship | Fishing Boat (Age of Empires), Fishing Ship (Age of Empires) | Dock | Stone, Bronze | 50 wood |
| Trade Boat → Merchant Ship | Trade Boat, Merchant Ship (Age of Empires) | Dock | Bronze, Bronze | 75 wood, 60 gold |
| Light Transport → Heavy Transport | Light Transport, Heavy Transport | Dock | Tool, Iron | 150 wood |
| Scout Ship → War Galley → Trireme | Scout Ship (Age of Empires), War Galley (Age of Empires), Trireme (Age of Empires) | Dock | Tool, Bronze, Iron | 135 wood |
| Catapult Trireme → Juggernaut | Catapult Trireme, Juggernaut (Age of Empires) | Dock | Iron, Iron | 135 wood, 50 gold |
| Fire Galley | Fire Galley (Age of Empires) | Dock | Iron | 115 wood, 40 gold |
| Trade Cart | Trade Cart (Age of Empires) | Market | Bronze (after Wheel) | 75 wood, 60 gold |

Two rules differ from AoE2: a Dock trains faster in each age (for example the Scout Ship: 70 s, then 46, 41 and
35 s; the "Time" of each ship page), and the Return of Rome tech tree removed the technology requirements of the
upgrades (page "Age of Empires II: Definitive Edition - Return of Rome", "Balance changes").

### 1.5 Technologies

Page "Technology (Age of Empires)" and the "Techbox" of the page of each technology.

| Technology | Wiki page | Building | Age | Cost | Time | Effect (short) |
|---|---|---|---|---|---|---|
| City Watch | City Watch | Town Center | Tool | 100 food | 15 s | buildings +3 sight |
| Woodworking | Woodworking | Market | Tool | 120 food, 75 wood | 60 s | woodcutters +20 %, +2 carry; missiles +1 range |
| Artisanship | Artisanship | Market | Bronze | 170 food, 150 wood | 80 s | the same again |
| Craftsmanship | Craftsmanship | Market | Iron | 240 food, 200 wood | 100 s | the same again |
| Stone Mining | Stone Mining (Age of Empires) | Market | Tool | 100 food, 50 stone | 30 s | stone miners +30 %, +3 carry; slingers +1 |
| Siegecraft | Siegecraft | Market | Iron | 190 food, 100 stone | 60 s | the same again; villagers vs. walls and towers |
| Gold Mining | Gold Mining (Age of Empires) | Market | Tool | 120 food, 100 wood | 50 s | gold miners +30 %, +3 carry |
| Coinage | Coinage (Age of Empires) | Market | Iron | 200 food, 100 gold | 60 s | gold mines +25 %, free tribute |
| Domestication | Domestication (Age of Empires) | Market | Tool | 150 food, 50 wood | 40 s | farms +75 food |
| Plow | Plow (Age of Empires) | Market | Bronze | 250 food, 75 wood | 75 s | farms +100 food |
| Irrigation | Irrigation (Age of Empires) | Market | Iron | 300 food, 100 wood | 100 s | farms +125 food |
| Wheel | Wheel | Market | Bronze | 175 food, 75 wood | 75 s | villagers +60 % speed |
| Toolworking | Toolworking | Storage Pit | Tool | 100 food | 40 s | melee +2 attack |
| Metalworking | Metalworking | Storage Pit | Bronze | 200 food, 120 gold | 75 s | melee +2 attack |
| Metallurgy | Metallurgy | Storage Pit | Iron | 300 food, 180 gold | 100 s | melee +3 attack |
| Leather Armor Infantry | Leather Armor Infantry | Storage Pit | Tool | 75 food | 30 s | infantry +2 melee armor |
| Scale Armor Infantry | Scale Armor Infantry | Storage Pit | Bronze | 100 food, 50 gold | 60 s | infantry +2 melee armor |
| Chain Mail Infantry | Chain Mail Infantry | Storage Pit | Iron | 125 food, 100 gold | 75 s | infantry +2 melee armor |
| Leather Armor Archers | Leather Armor Archers | Storage Pit | Tool | 100 food | 30 s | archers +2 melee armor |
| Scale Armor Archers | Scale Armor Archers | Storage Pit | Bronze | 125 food, 50 gold | 60 s | archers +2 melee armor |
| Chain Mail Archers | Chain Mail Archers | Storage Pit | Iron | 150 food, 100 gold | 75 s | archers +2 melee armor |
| Leather Armor Cavalry | Leather Armor Cavalry | Storage Pit | Tool | 125 food | 30 s | cavalry +2 melee armor |
| Scale Armor Cavalry | Scale Armor Cavalry | Storage Pit | Bronze | 150 food, 50 gold | 60 s | cavalry +2 melee armor |
| Chain Mail Cavalry | Chain Mail Cavalry | Storage Pit | Iron | 175 food, 100 gold | 75 s | cavalry +2 melee armor |
| Bronze Shield | Bronze Shield | Storage Pit | Bronze | 150 food, 180 gold | 50 s | infantry, slingers +1 pierce armor |
| Iron Shield | Iron Shield | Storage Pit | Iron | 200 food, 320 gold | 75 s | infantry, slingers +1 pierce armor |
| Tower Shield | Tower Shield | Storage Pit | Iron | 250 food, 400 gold | 100 s | infantry, slingers +1 pierce armor |
| Architecture | Architecture (Age of Empires) | Government Center | Bronze | 150 food, 175 wood | 50 s | buildings +20 % HP, build 33 % faster |
| Logistics | Logistics (Age of Empires) | Government Center | Bronze | 180 food, 100 gold | 60 s | barracks units take 1/2 population |
| Nobility | Nobility | Government Center | Bronze | 175 food, 120 gold | 70 s | cavalry (not elephants) +15 % HP |
| Urbanization | Urbanization | Government Center | Bronze | 300 wood, 100 stone | 45 s | houses give double population |
| Writing | Writing | Government Center | Bronze | 200 food, 75 gold | 30 s | shared exploration with allies |
| Alchemy | Alchemy | Government Center | Iron | 250 food, 200 gold | 100 s | missiles +1 attack, Fire Galley +6 |
| Aristocracy | Aristocracy | Government Center | Iron | 175 food, 150 gold | 60 s | academy units +0.225 speed |
| Ballistics | Ballistics (Age of Empires) | Government Center | Iron | 200 food, 50 gold | 60 s | missiles hit moving targets |
| Conscription | Conscription (Age of Empires) | Government Center | Iron | 450 food, 250 gold | 60 s | land military units train 25 % faster |
| Engineering | Engineering | Government Center | Iron | 200 food, 100 wood | 70 s | siege units and ships +2 range and sight |
| Polytheism | Polytheism | Temple | Bronze | 120 gold | 50 s | priests +40 % speed |
| Mysticism | Mysticism | Temple | Bronze | 120 gold | 50 s | priests +20 HP |
| Astrology | Astrology | Temple | Bronze | 175 gold | 50 s | conversion and heal +30 % |
| Medicine | Medicine | Temple | Iron | 150 gold | 50 s | priests heal +100 % |
| Monotheism | Monotheism | Temple | Iron | 350 gold | 75 s | priests convert buildings and priests |
| Afterlife | Afterlife | Temple | Iron | 275 gold | 75 s | priests +3 range and sight |
| Fanaticism | Fanaticism (Age of Empires) | Temple | Iron | 150 gold | 60 s | priests rest 50 % shorter |
| Zealotry | Zealotry (Age of Empires) | Temple | Iron | 120 gold | 60 s | villagers +7 attack, +40 HP, -8 carry |
| Theocracy | Theocracy (Age of Empires) | Temple | Iron | 400 gold | 100 s | only one priest of a group rests |

The Granary researches the walls and towers of each age (page "Granary (Age of Empires)"): Small Wall and Watch
Tower (Tool Age), Medium Wall and Sentry Tower (Bronze Age), Fortified Wall, Guard Tower and Ballista Tower (Iron
Age, the Ballista Tower after Ballistics). Their costs are on the page of each wall and tower.

### 1.6 The civilization bonuses that are not done yet (#3667, #3827)

`game/data/antiquity/civs.jsonl` has the 17 civilizations with the bonus texts of the wiki. #3827 added the bonuses of
the units and buildings: costs, hit points, armor, range, fire rate, walk speed, free technologies, the Babylonian
priest faith, the Phoenician dock sight and the Yamato fishing boats. A `units` rule can name a list of units, because
the Antiquity units have no AoE2 groups (`civs.changes`). The missing units and technologies of the wiki pages (section
"Characteristics") are the key `"not_civs"` of the items in `game/data/antiquity/train.jsonl` and `build.jsonl`
(`civs.MISSING`). The Phoenician dock has +25 % hit points: +150 of the 600 of the Return of Rome dock.

These bonuses do not work yet. Each needs a feature that the game program does not have:

- Choson: towers +2 range. No key changes the range of a building.
- Palmyrans: camel speed and +20 % trade gold work (`trade_gold`, #4446); tributes without tax do not. No key changes them.
- Team bonuses (the key `"team"`, #4452: it counts for the player and each ally, `civs.Team`): 13 of 17 work. Only
  their text: Macedonian houses +50 hit points (the key `"hp"` holds a factor, not added hit points), Phoenician archers
  +2 line of sight (no key for the sight of a unit), Roman priests heal 50 % faster (no key for the heal speed), Shang
  town centers +4 population room (`"housing"` replaces the population of a building, it does not add to it).

## 2. The data structure of a second rule set

### 2.1 The present structure

- 23 modules of `game/` read their rules from `game/data/*.jsonl` with `table.load` **at import** and build module
  tables from them (`train.ROWS`, `build.AGE_TECHS`, `civs.ROWS`, `combat.STATS`, `gather.ROWS`, `bot.ORDER` ...).
  A rule set chosen later than the import does not reach these tables.
- One game program process plays one game (`run.main`). `run.py` and `savegame.py` import no rule module at import,
  and `run.main` imports the first one (`civs`, in `civ_choices`) after it reads the options and the saved settings
  (`savegame.settings`). `tests/test_antiquity_data.py` checks this in a child process.
- Many Return of Rome names are AoE2 names with other values: `TOWN_CENTER`, `HOUSE`, `BARRACKS`, `DOCK`,
  `MARKET`, `STONE_MINING`, `GOLD_MINING`, `COINAGE`, `ARCHITECTURE`, `LONG_SWORDSMAN`, `LEGIONARY`, `CENTURION`,
  `TRADE_CART`, `WAR_GALLEY`, `FIRE_GALLEY`. `table.load` stops on two lines of one name in one file.
- The code names few game objects (`tests/data/game_names_in_code.txt` has no line left): the menus, the drop
  sites, the age requirements, the bot build order and the combat values are data.

### 2.2 The options

| Option | For | Against |
|---|---|---|
| A. A folder per rule set, `game/data/antiquity/`, chosen once per process before the rule modules load | No change to the 23 readers. Each rule set has its own names: `TOWN_CENTER` of Antiquity Mode is its own line. The code that names `TOWN_CENTER`, `HOUSE`, `VILLAGER` works in both sets. | The tests of one pytest process see only one rule set: the behaviour tests of Antiquity Mode run in a child process. |
| B. A key `"rules"` on the lines of the present files | One file per topic. | Two lines of one name (`STONE_MINING`: 100 food and 75 wood in AoE2, 100 food and 50 stone in Return of Rome) are not possible: the names must change (`ROR_STONE_MINING`), and then the code that names `TOWN_CENTER` does not find the Antiquity line. Each of the 23 readers must filter by the rule set. Still an import-time choice. |
| C. Tables per game (`g.rules`) in place of module tables | Two rule sets in one process. | Each of the 23 modules and their tests change (hundreds of lines), for no player benefit: a game uses one rule set. |

**Choice: option A.** It is clearly the best, so this ticket makes no decision ticket. Reasons: the mode is
separate in AoE2 (one rule set per game, section 1); it changes one function (`table.load`) and not 23 modules
(principle P10: fix the cause in one place, with a check); it keeps the AoE2 data and tests as they are (P3: the
default stays); the converted world keeps working, because the Antiquity lines of the jobs that both games have
use the AoE2 names.

### 2.3 How option A works

1. `table.RULES` is the rule set of the process: `os.environ.get("AOE2MC_RULES", "aoe2")`. `table.use(name)` sets
   it, and stops with an error when a rule file was loaded already (a list `table.LOADED` of the loaded file
   names): so no module can keep the AoE2 rows by mistake. `run.main` calls `table.use("antiquity")` for
   `--antiquity`, just after `savegame.settings` and before `civ_choices`.
2. `table.load(path, rules=None)` reads `game/data/<rules>/<path>` when it exists, else `game/data/<path>`:
   - The item files (`civs.jsonl`, `train.jsonl`, `build.jsonl`): the file of the rule set **replaces** the AoE2
     file. These files are lists that the menus, the `--civ` choices and the age rules show in full: an AoE2 line
     must not show in Antiquity Mode.
   - The value files (`units.jsonl`, `buildings.jsonl`, `gather.jsonl`, `monk.jsonl`, `sounds.jsonl`): the lines of
     the rule set **add to** the AoE2 lines; a line of the same name replaces the AoE2 line. These files are
     lookups by name: the AoE2 objects of a converted world (a `MILL`, a `KNIGHT` of the scenario) keep values.
     One set `table.ADD` names these files (one per line, alphabetical).
   - The other files (`setup.jsonl`, `difficulty.jsonl`, `cheats.jsonl`, `taunts.jsonl`, `replay.jsonl`, the
     `*_keys.jsonl` files) have no copy: the lobby, the cheats, the taunts and the documentation of the keys are the
     same for both sets. A new key of an Antiquity line is one line in the `*_keys.jsonl` file (`docs/extend.md`).
3. Names: an Antiquity item with the same job as an AoE2 item uses the AoE2 name (`TOWN_CENTER`, `HOUSE`,
   `BARRACKS`, `DOCK`, `MARKET`, `FARM`, `ARCHERY_RANGE`, `STABLE`, `SIEGE_WORKSHOP`, `WONDER`, `WATCH_TOWER`,
   `GUARD_TOWER`, `FISHING_SHIP`, `TRADE_CART`, `VILLAGER_MALE` and `VILLAGER_FEMALE`). A new item gets the wiki
   name in capitals with `_` (`GRANARY`, `STORAGE_PIT`, `GOVERNMENT_CENTER`, `ACADEMY`, `TEMPLE`, `HOPLITE`,
   `TOOL_AGE`, `BRONZE_AGE`, `IRON_AGE`). The AoE2 buildings of a converted world get an Antiquity line in
   `buildings.jsonl` with the key `"as"` (`combat.STANDS_FOR`) and `"menus"`: `MILL` as `GRANARY`, `LUMBER_CAMP`
   and `MINING_CAMP` as `STORAGE_PIT`, `MONASTERY` as `TEMPLE`, `CASTLE` as `GOVERNMENT_CENTER`.
4. Tests: a data test reads the rule set in the test process with `table.load(name, rules="antiquity")`. A
   behaviour test (a fake server game, a training, an age-up) runs its code in a child process with
   `AOE2MC_RULES=antiquity` (`subprocess.run([sys.executable, "-c", CODE], env=...)`), and prints JSON for the
   asserts. One child costs about one second of imports: put the checks of one ticket into one child.

### 2.4 The functions that change

| Place | Change | Step |
|---|---|---|
| `table.load`, new `table.RULES`, `table.ADD`, `table.use`, `table.LOADED` | the rule set folder (2.3) | #3666 |
| `train.DATA` | the name `"train.jsonl"` in place of the path (a path skips the rule set folder) | #3666 |
| `run.SETTINGS`, `run.main` (`--antiquity`, `table.use`), `savegame.SETTINGS` | the lobby setting; a saved Antiquity game loads Antiquity Mode again (`savegame.settings` runs before `table.use`) | #3666 |
| `train.AGES`, the two age-name tuples of `build.locked` | the age names from the data (the labels of the age lines), not a literal | #3666 |
| `build.AGE_TECHS`, `train.REQUIRES`, `train.STARTS` | no code change: the lines `TOOL_AGE`, `BRONZE_AGE`, `IRON_AGE` with `"age_tech"` and `"requires"` | #3666 |
| `techtree.AGES = 4` | no change: Return of Rome has four ages too | — |
| `replay.AGES` | no change: `--antiquity` with `--replay` stops with an error (the records are AoE2 games) | #3666 |
| `run.civ_choices`, `civs.ROWS` | the 17 civilizations; a scenario civilization that is not in the rule set gets one of them (a new key, for example `"stands_for"`) | #3667 |
| `.gitattributes`, `packaging/aoe2mc.spec`, `tools/data_lint.py`, `tests/test_data_keys.py` (`os.listdir(table.DIR)` sees the folder) | the merge driver, the bundle and the checks of the data files see `game/data/antiquity/*.jsonl` | #3666 |

## 3. Which AoE2 lines Antiquity Mode uses again

- The same structure for the same rule: an age line (`"age_tech"`, `"requires": [2, [...]]`), a building line of
  `build.jsonl` (`"cost"`, `"time"`, `"age"`, `"bot"`, `"near"`), a menu line of `train.jsonl` (`"building"`,
  `"slot"`, `"upgrade"`, `"effect"`), a civilization line with the present keys of `civ_keys.jsonl`.
- The AoE2 lines of `units.jsonl`, `buildings.jsonl`, `gather.jsonl`, `monk.jsonl` and `sounds.jsonl` stay for the
  objects of a converted world (2.3, "add to").
- The game modes and the lobby (`setup.jsonl`) name AoE2 items (Regicide: `KING`, a `CASTLE`; Empire Wars: AoE2
  buildings). `--antiquity` starts with `--mode standard` only; the Return of Rome modes are not in the scope of
  #3664.
- New keys (a line in the `*_keys.jsonl` file each): the building that must stand first ("Unlocks" in 1.3), the train
  time of a Dock in each age (1.4), the food types of a drop site (the Granary and the Storage Pit, 1.3).

## 4. The steps of the full scope of #3664

| Item of #3664 | Step | Size | Files |
|---|---|---|---|
| 2. The setting `--antiquity` | #3666: the rule set folder (2.3), the setting, the save, the checks of the data files | M (with item 3) | `game/table.py`, `game/run.py`, `game/savegame.py`, `game/train.py`, `.gitattributes`, `packaging/aoe2mc.spec`, `tools/data_lint.py`, `tests/test_data_keys.py`, a new `tests/test_antiquity_setting.py` |
| 3. The four ages | #3666: `TOOL_AGE`, `BRONZE_AGE`, `IRON_AGE` and the villager at the Town Center; the age names from data | (in #3666) | `game/data/antiquity/train.jsonl`, `game/data/antiquity/build.jsonl`, `game/build.py`, `game/train.py` |
| 4. The civilizations | #3667: 17 lines with the bonuses of the civilization pages; the missing units and technologies (`"missing"`); a list in this document of each bonus that the code cannot do yet | M | `game/data/antiquity/civs.jsonl`, `game/data/civ_keys.jsonl`, `game/run.py` (`civ_choices`), a new `tests/test_antiquity_civs.py` |
| 5. The buildings and their menus | #3668: the 25 buildings of 1.3 (cost, age, footprint, "Unlocks"), the drop sites, the `"as"` lines of the AoE2 world buildings, the wall and tower researches of the Granary | M | `game/data/antiquity/build.jsonl`, `game/data/antiquity/buildings.jsonl`, `game/data/antiquity/gather.jsonl`, `game/data/antiquity/train.jsonl`, `game/build.py` (the "Unlocks" key), `buildings.py` `select()` names, a new `tests/test_antiquity_buildings.py` |
| 6. The units | #3669: the land units of the Barracks, Archery Range, Stable and Academy (1.4) with their values and upgrades | M | `game/data/antiquity/train.jsonl`, `game/data/antiquity/units.jsonl`, `units.py` (`classify`: the mob of each new name), a new `tests/test_antiquity_units.py` |
| 6. The units (rest) | a new ticket: the units of the Siege Workshop, Temple, Dock and Market; the Dock train time of each age | M | the same data files, `game/train.py` (the time of each age), a new `tests/test_antiquity_ships.py` |
| 7. The technologies | a new ticket: the 47 technologies of 1.5 with `"effect"`; the groups of the effects (`"groups"` in `units.jsonl`: infantry, archers, cavalry, priests) | M | `game/data/antiquity/train.jsonl`, `game/data/antiquity/units.jsonl`, a new `tests/test_antiquity_techs.py` |
| 8. The bots | a new ticket: the bot build order (`"bot"`, `"near"` on the Antiquity buildings) and a fake server test of a bot that advances to the Tool Age | S | `game/data/antiquity/build.jsonl`, a new `tests/test_antiquity_bot.py` |

Order: #3666 first (the other steps need the folder), then #3667 and #3668 in parallel, then #3669, then the rest of
the units, the technologies and the bots, then the check ticket (item 9).

## 5. Open points

- The start resources of Antiquity Mode: the wiki pages above do not give them. #3666 reads them from the page of
  the lobby setting (search "Starting resources") and keeps the AoE2 values until then.
- The look of the new buildings (Granary, Storage Pit, Government Center, Academy, Temple): `buildings.select()`
  gives a design by name; a building without a design gets `generic`. A new design is a `design` ticket.
- The technology effects (#3714): all work since epic #3887; the table of its sub-issues is on the epic.
