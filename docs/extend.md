# Where a new item goes

Read this file before you add a new item, key, setting, mode, plugin command or trigger type, or a test of a data
file (`CLAUDE.md`, "Code style"). Each rule puts the new thing in one line of a data file or a table, so that
parallel tickets do not change the same lines. Most rules have a check: `tools/data_lint.py`,
`tests/test_data_files.py`, `tests/test_data_keys.py`, `tests/test_conflict_prone.py` and the merge driver
`tools/merge_jsonl.py`.

- Never test the number of entries of a data table (`len(combat.SIGHT) == 154`): each new line changes it, and parallel
  tickets conflict there. Test the values (owner, #2008; `tests/test_conflict_prone.py`).
- A new menu item of a building (cost, time, slot, help, age) is one new line in `game/data/train.jsonl`, at the end of
  its building block (a technology also gets its key `"effect"`: the change of the combat values, `train.effect()`, #2029): the merge driver `tools/merge_jsonl.py` (`merge=jsonl`, #2004) merges the lines by name (a line that both sides changed: by key and list item, #2064), and `train.load()` stops on a name in two lines (#1702).
- A menu test checks only its own item (`item()` of `tests/menu_line.py`), never the whole menu line: one `order()` test per
  building checks the full menu from the data (#2099).
- The combat values of a new unit are one new line in `game/data/units.jsonl` (`combat.STATS`, #1912), of a new building
  one in `game/data/buildings.jsonl` (`combat.BUILDINGS`); its line of sight is the key `"sight"` there (#1913; epic #1909 moves more tables).
- The select voice of a unit class is one line in `game/data/sounds.jsonl` (`gather.VOICES`, the vanilla sound events "select" and "order" (#3500) and the pitch; `Gather.voice_class` maps a unit to its class, #3499).
- The converter tables are lines in `data/*.jsonl` too (#1917): an animal in `animals.jsonl`, an infantry design in `lines.jsonl`, a footprint in `footprint.jsonl` (the first match wins: put a longer name before its part).
- An item that few civilizations have (a unique or regional unit, building or technology) gets the key `"civs"` (the
  civilizations that have it, sorted) on its own line of `game/data/train.jsonl` or `game/data/build.jsonl`
  (`civs.ONLY`, #2235). An item that most civilizations have gets the key `"not_civs"` (the civilizations without it,
  sorted) on its line (`civs.NOT`, #3200; `civs.MISSING` joins both). Neither changes `game/data/civs.jsonl`: a change
  of many civ lines made each parallel PR `dirty` on GitHub. The civ lines hold the bonuses (`unique`, `costs`, `units`,
  `twice`), not `civs.py`.
- A new key of `game/data/civs.jsonl` (a civilization bonus) is one line in `game/data/civ_keys.jsonl` (what it does, its
  issue) and `civs.value("key", civ, default)` in the module that applies it: no new table or comment in `game/civs.py` (#2281).
- A new key of `game/data/train.jsonl` is one line in `game/data/train_keys.jsonl` and `train.value("key", name, default)`
  in the module that reads it, not a new table of `game/train.py` (#2507).
- A special effect of a technology at its research is a function `(g, entry)` in its own module and the key
  `"on_research"` (`"module.function"`) on its line, not an `if` block in `train.research()` (#3243).
- A new key of `game/data/setup.jsonl` (a game mode, a lobby setting) is one line in `game/data/setup_keys.jsonl` (`"type"`,
  `"kind": true` for a key of the "one kind" rule, `"text"`, `"issue"`), not a change of `check_setup()` in `tests/test_data_files.py` (#2558).
- A new data line needs no test of its values: `tests/test_data_files.py` checks the form of each line of `game/data/`
  (keys, types, names that exist, #1916), and `tests/test_data_keys.py` checks that the code reads each key (#2188): a new key needs no test line. Test the behavior that the code computes
  from it (a fight, a menu, a bonus).
- A new command of the Paper plugin: its line in the command list at the top of `AoePlugin.java` and its
  `if` block in `onCommand` go in alphabetical order of the command name, not after the last one (#795 and #813 conflicted).
- A new game setting of `game/run.py` (a lobby setting, epic #2263) is one line in `run.SETTINGS` and an option of the
  same name, not a new keyword of `play()` (#2373).
- A new part of the saved game is one function `(x, p)` or `(g, d)` and one line in `SIDE_STEPS` or `GAME_STEPS` of
  `game/savegame.py`, not a new block in `load()` (#3484).
- A new game mode (`--mode`) is one line in `game/data/setup.jsonl` (keys `"help"`, `"module"`, `"age"`, `"loaded"`,
  `"bots"`: `run.MODES`) and its module with `setup(g, mode)`, not a change of `play()` (#2521).
- A new trigger effect of the converter is one line in `aoe2mc.EFFECTS` (its ID constant on its own line, both in
  alphabetical order), its handler `x_lines(e, c)` and the keys that it reads from the scenario effect one line
  in `aoe2mc.EFFECT_KEYS` (#2792), not a change of `trigger_files` (#2613) or `read_scenario`; a condition on a score
  is one line in `aoe2mc.SCORE_TESTS` (#2704), a condition of the tick function one line in `aoe2mc.TICKED` (#2769). The keys of a new
  condition are one line in `aoe2mc.CONDITION_KEYS`, a new aoe2mc.json list of the scenario mode one line in
  `aoe2mc.TRIGGER_LISTS` (both in alphabetical order, #2832). A new order of the scenario mode (`game/scenario.py`) is one line in
  `scenario.ORDER_KINDS` and its handler at the end of the handlers in `orders()`, not a change of its docstring. The
  datapack text of a trigger type (`tools/triggers.py` `MAP`) is its line in `data/trigger_conditions.jsonl` or `data/trigger_effects.jsonl`.
