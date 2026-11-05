# XS scripts of AoE2 DE (epic #5119)

XS is the C-like script language of AoE2 DE. A scenario calls it from its triggers (the effect and the condition
"Script Call"), from its map script (`--xs FILE`) and a random map from `#includeXS`. The owner chose both ways to run
it (#5120, 2026-10-31: "A and B"):

- A: the interpreter in the game program: `xs.py` (the parser, #5121), `game/xs_run.py` (#5610),
  `game/xs_host.py` (the game functions, #5623), `game/scenario.py` (the map script, #5662).
- B: the converter compiles XS to datapack functions, so that a vanilla world (no game program) runs it. This
  document is the plan of B (#5667).

## XS as datapack functions

Minecraft feature: datapack functions and scoreboards (vanilla, no plugin). XS has a value stack, functions and
timed rules. Scoreboards hold 32-bit integers, `scoreboard players operation` has `+= -= *= /= %= = < > ><`,
`execute if score` tests, a function can call itself, `return` leaves a function, and a macro function (`$` lines,
`function ... with storage`) puts a value into a command.

### The form

- A new module `xs_mc.py` (next to `xs.py`) compiles the tree of `xs.parse` to the files
  `data/aoe2mc/function/xs/...` of the pack `datapacks/aoe2mc`. `trigger_files()` adds them and the tick lines.
  The input is the map script (aoe2mc.json `"xs_script"`, #5122) and the code of the Script Call triggers (`xs_list`).
- The objective `aoe_xs` holds all values. A global variable is the holder `#g.<name>`. A parameter or a local
  variable of the function F is `#l.F.<name>` (no recursion, see below: one holder per variable is correct).
  The temporary values of an expression are `#x<k>`, the return value of F is `#r.F`.
- `main()` runs once, in the first tick with a player on the server. The score `#main aoe_xs` marks it.
  The clock is `#now aoe_xs`: the tick function adds 1 each tick (20 per second). The rule `R` has the holders
  `#on.R` (enabled), `#due.R` (the next tick) and `#min.R` (the interval in ticks).
- Minecraft saves the scores with the world (`data/scoreboard.dat`): a saved vanilla world keeps the variables and
  the rule states with no code.

### The table

| XS part | Datapack form | Limit |
|---|---|---|
| `int` | A score. `= + - *` are `scoreboard players operation`. `/` and `%`: Minecraft rounds down (`floorDiv`), XS truncates toward zero as C: two more lines correct the sign | Division by 0: the score stays, the statement goes on (A stops the call) |
| `bool` | A score 0 or 1. `== != < <= > >=`: `execute store success score ... if score ...`. `!`: `1 - x` | — |
| `float` | Fixed point: a score of the value × 1000. `+ -` as `int`. `*`: (a / 1000) × b + (a % 1000) × b / 1000, so that a product that fits does not overflow. `/`: q = a / b, then q × 1000 + (a % b) × 1000 / b | 3 decimal places, range ±2 147 483. A quotient is exact to 0.001 while the divisor is less than 2147 |
| `string` | A literal in `xsChatData` and a literal rule or group name: compile (the text goes into the command) | A string variable, `+` of strings, a string compare: the game program only (scores have no text) |
| `vector` | Three `float` holders `.x .y .z`; the operators work on each part | As `float` |
| `const` | The compiler puts the value into each use (no holder) | — |
| `static` | A static local is a global holder `#s.F.<name>` | — |
| `extern` | A global holder (a Script Call of a trigger can read it) | — |
| Functions, `return` | One function `xs/f/<F>` per XS function. The caller sets the parameter holders, then runs it. `return x` sets `#r.F` and the flag `#ret`; each sub-function call of the body is `execute if score #ret aoe_xs matches 1 run return 0` after it | — |
| A call with a return value inside an expression | The compiler moves the call before the statement into a temporary holder. `&&` and `\|\|` keep the short circuit: the right side is a sub-function that runs `if score` the left side | — |
| Recursion (a call cycle) | None: the holders of the locals are shared, a datapack has no stack | The game program only: the compiler finds the cycle in the call graph |
| `if`, `else` | `execute if score ... run function xs/b/<k>` (a sub-function per block) | — |
| `while`, `for` | A sub-function that tests the condition, runs the body and calls itself | One tick runs at most the commands of the game rule of the command chain (default 65 536): a longer loop stops in that tick (A stops after 200 000 steps) |
| `break`, `continue` | The flags `#brk` and `#cont`, tested after each statement of the loop body | — |
| `switch` | One `execute if score ... matches N` line per `case` sets the number of the case; one sub-function per case. As A (`game/xs_run.py`): only the first case with the value (else `default`) runs, no fall-through to the next case | A computed `case` label: the game program only |
| The operators `++ -- += -= ...` | `scoreboard players add` / `remove` / `operation` | — |
| `include` | The file is in the AoE2 profile folder, not in the scenario | A and B: one warning line with the file name |
| `rule`, `active`, `inactive` | `#on.R` is 1 or 0 at the start | — |
| `minInterval`, `maxInterval` | `#min.R` = min(minInterval, maxInterval) × 20 ticks (as A); the tick line `execute if score #on.R matches 1 if score #now >= #due.R run function xs/r/R` | — |
| `highFrequency` | The rule runs in each tick | AoE2 runs it each game frame |
| `runImmediately` | `#due.R` = `#now` at the start and at `xsEnableRule` | — |
| `priority` | The order of the rule lines in the tick function (a higher priority first) | `xsSetRulePriority` and `xsSetRulePrioritySelf` change nothing: one warning line |
| `group` | The compiler knows the rules of each group | — |
| `xsEnableRule`, `xsDisableRule`, `xsDisableSelf` | Set `#on.R` (and `#due.R`) | The name must be a literal: else the game program only |
| `xsEnableRuleGroup`, `xsDisableRuleGroup`, `xsIsRuleGroupEnabled` | The lines of each rule of the group | As above |
| `xsIsRuleEnabled` | `#on.R` | As above |
| `xsSetRuleMinInterval`, `xsSetRuleMaxInterval` (and `Self`) | Set `#min.R` | As above |
| `xsGetTime` | `#now` × 50 (milliseconds) | — |
| `xsChatData` | `tellraw @a` with the text and a score component for `%d` | A `float` value shows its whole part |
| `xsBreakPoint` | No command | — |
| `xsGetGameTime` | `#now` / 20 | — |
| `xsArrayCreate*`, `xsArrayGet*`, `xsArraySet*`, `xsArrayResize*`, `xsArrayGetSize`, `xsDumpArrays` (each type: Bool, Float, Int, String, Vector) | None | The game program only (`Xs.arrays`, #5838): an array is a list of values with an index that the script computes, and a vanilla score holds one number. A storage list could hold the values, but each get and set with a computed index needs a macro function, and a float or vector array has no score form. The converter keeps the warning line |
| `xsTriggerVariable`, `xsSetTriggerVariable` | The score `#v<N> aoe_var` (the converted triggers use it, `trigger_files()`) | A literal N: one command. A computed N: a macro function |
| `xsGetObjectCount` | `execute store result score ... if entity @e[tag=aoe2mc.p<P>,tag=aoe2mc.t<ID>,tag=!<MOUNT>]`, as `count_lines()` | A building is a block with no entity: it does not count (as "Count Units into Variable"). A computed P or ID: a macro function |
| `xsGetObjectCountTotal` | As `xsGetObjectCount` | A vanilla world has no training queue and no construction site: the count of the done units |
| `xsGetPlayerCivilization` | A constant: the converter knows the civilization of each player | — |
| `xsGetTechState`, `xsResearchTechnology`, `xsGetTechName`, `xsSetTechName`, `xsIsObjectAvailable`, `xsGetTechAttribute`, `xsSetTechDescription`, `xsInitiateResearch`, `xsResearchLocalTechnology`, `xsHasResearchedLocalTechnology` | None: a vanilla world has no technologies and no menus (#5840) | The game program only. There `xsEffectAmount` does `cModResource`, `cMulResource` and `cEnableObject`; the unit attribute effects, `xsGetTechAttribute`, `xsSetTechDescription`, `xsInitiateResearch` and the local technologies keep the warning line (no attribute table, no description text, no research by building ID) |
| `xsPlayerAttribute`, `xsSetPlayerAttribute`, `xsEffectAmount`, `xsGetPlayerNumberOfTechs` | None: a vanilla world has no stock, no attributes and no technologies (`resource_lines()` only stores the changes for the game program) | The game program only |
| `xsCreateFile`, `xsOpenFile`, `xsCloseFile`, `xsWriteInt/Float/String/Vector`, `xsReadInt/Float/String/Vector`, `xsGetFilePosition`, `xsSetFilePosition`, `xsOffsetFilePosition`, `xsGetFileSize` | None: a datapack cannot write or read a binary file (#5845) | The game program only: the files `xs/<name>.xsdat` of the world (`xs_host.files`). A name with `/` or `..`: one warning line. `xsOffsetFilePosition` goes only forward |
| `xsGetMapWidth`, `xsGetMapHeight`, `xsGetMapSeed`, `xsGetNumPlayers`, `xsGetMapTileAttribute` (literal x, y), `xsGetContextPlayer`, `xsSetContextPlayer`, `xsGetWorldPlayerId`, `xsGetHandicapMultiplier` (#5839) | Constants: the converter knows the map, the players and the side of the script | A computed tile: the game program only |
| `xsGetWorldTime`, `xsGetTurn` (#5839) | `#now` × 50 and `#now` (one turn per tick) | — |
| `xsGetRandomNumber`, `xsGetRandomNumberLH`, `xsGetRandomNumberMax`, `xsGetMapName`, `xsGetPlayerName`, `xsGetPlayerInGame` (#5839) | None yet: `random value` gives other numbers than the seeded generator of A; the strings and the defeat state have no score | The game program only |
| `xsAddRuntimeEvent`, `xsGetFunctionID`, `xsGetDataTypeSize`, `xsGetDifficulty`, `xsGetLocale`, `xsGetMapID`, `xsGetPlayerType` (#5839) | None | A and B: the warning line (the game program has no runtime events, no locale and no map ID) |
| `xsSetDiplomacy`, `xsDeclareVictory` (victory true), `xsSetPlayerColor` | The commands of the trigger effects "Change Diplomacy", "Declare Victory" and "Change Player Color" (`diplomacy_lines()`, `victory_lines()`, `color_lines()`) | A computed player or stance: a macro function. `xsDeclareVictory` with victory false (a defeat): no form in A and B, one warning line (#5843) |
| `xsGetVictoryCondition`, `xsGetVictoryConditionForSecondaryGameMode`, `xsGetVictoryType`, `xsGetCivName` | A constant: the converter knows the victory settings and the civilizations | — |
| `xsGetDiplomacy`, `xsGetPlayerCivName`, `xsGetPlayerColorTag`, `xsSetPlayerName`, `xsSetPlayerCivName`, `xsGetVictoryTime`, `xsGetVictoryPlayer` (and `ForSecondaryGameMode`) | None: the stances, the names and the wonder, relic and hill timers are in the game program (`game/xs_host.py`, #5843); strings are no scores | The game program only |
| `xsGetGoal`, `xsSetGoal`, `xsGetStrategicNumber`, `xsSetStrategicNumber`, `xsGetAiSignal`, `xsSetAiSignal`, `xsGetAiScriptGoal`, `xsSetAiScriptGoal`, `xsSetContextPlayer`, `xsGetContextPlayer` | None: a vanilla world has no AI script (`game/per.py` runs it in the game program) | The game program only (#5846): the AI script of the context player (default: the first bot with a script). A strategic number by its id (`per_numbers.jsonl`). An AI script goal is the trigger event of `(event-detected trigger N)`. `useLegacyAi` has no effect |
| `xsGetGroupMoveTarget` | None | No form: the AI runtime has no unit groups with a move target. It keeps the warning line |
| The unit reads of #5837 and #5847: `xsGetGarrisonedInUnitId`, `xsGetGarrisonedUnitIds`, `xsGetPlayerUnitIds`, `xsGetUnitAttribute`, `xsGetUnitBuildPoints`, `xsGetUnitCaption`, `xsGetUnitGatherPoint`, `xsGetUnitMoveTarget`, `xsGetUnitPlayerName`, `xsGetUnitTargetUnitId`, `xsGetUnitType`, `xsDoesUnitExist`, `xsGetPlayerNumberOfObjects`, `xsGetUnitAttributeHeld`, `xsGetUnitCivName`, `xsGetUnitClass`, `xsGetUnitCopyId`, `xsGetUnitHitpoints`, `xsGetUnitName`, `xsGetUnitObjectId`, `xsGetUnitOwner`, `xsGetUnitPosition`, `xsIsObjectValid` | None now: a vanilla world has no map of XS id -> entity (the game program keeps it: `xs_host.ids`). A later form: a tag `aoe2mc.r<ref>` on each start entity and `execute if entity` / `data get entity` | The game program only |
| The unit changes of #5841: `xsCreateUnit`, `xsRemoveUnit`, `xsSetUnitHitpoints`, `xsSetUnitOwner`, `xsSetUnitPosition`, `xsSetUnitName`, `xsSetUnitCaption`, `xsFlashUnit`, `xsStopUnit`, `xsTaskUnits`, `xsSetUnitAttributeHeld`, `xsSetUnitBuildPoints`, `xsSetUnitGatherPoint`, `xsTrainObject` | None now: a vanilla world has no map of XS id -> entity. A later form: the commands of "Create Object", "Remove Object", "Change Object HP", "Change Ownership" and "Task Object" on the tag `aoe2mc.r<ref>` | The game program only: `summon`, `kill`, `data modify entity`, `team join`, `tp`, `effect give ... glowing`, `aoe moveto`, `aoe attack`, the stock of a villager, the site progress, `train.rally` and `train.queue`. `xsRemoveUnit` of a building: the warning line (a building is blocks). `xsBuildUnit`, `xsSetUnitCharge`, `xsSetUnitProperty`, `xsSetUnitCivName`, `xsSetUnitPlayerName`: no form (no build order by id, no charge, no property table, no own name per unit): the warning line |
| `xsGetObjectAttribute`, `xsGetObjectClass`, `xsGetObjectType`, `xsGetObjectName`, `xsGetDamageClassName`, `xsGetObjectAttributeName`, `xsGetPlayerAttributeName`, `xsTaskAmount`, `xsGetTaskAmount`, `xsResetTaskAmount` (#5842) | None: a vanilla world has no unit kind data and no task list | The game program only (`game/xs_host.py`) |
| `xsTask`, `xsRemoveTask`, `xsModifyObjectTasks`, `xsModifyUnitTasks`, `xsObjectTaskAmount`, `xsUnitTaskAmount`, `xsGetObjectTaskCount`, `xsObjectHasAction`, `xsGetObjectCopyId`, `xsSetObjectDescription` (#5842) | None: the game program has no task list and no description of a unit kind (mob AI does the tasks) | No form: the warning line |
| The screen functions of #5844: `xsSendChat`, `xsDisplayInstructions`, `xsClearInstructions`, `xsDisplayTimer`, `xsClearTimer`, `xsUnsyncGetTimerTimeRemaining`, `xsPlaySound`, `xsSetViewPosition`, `xsUnsyncGetViewPosition`, `xsUnsyncGetLocalPlayerId`, `xsUnsyncGetPlayerSelectedUnitIds`, `xsUnsyncIsUnitVisible` | A literal text, time and player can use the commands of the trigger effects (`chat_lines()`, `instruction_lines()`, `timer_lines()`, `sound_lines()`, `view_lines()`) in a later ticket | Until then: the game program only (`xs_host.screen`; a timer is a boss bar that `xs_host.timers` updates each game second). The view reads, the selection and the visibility need the game program. No form in A and B (the warning line): `xsSetZoom`, `xsUnsyncGetZoom` (Minecraft has no zoom command: the field of view is a client option), `xsSetColorMood`, `xsGetColorMood` (no color mood ID in the game program; the converter maps the effect, `mood_lines()`), `xsGetString` (the string table of the AoE2 game files is not in the world), `xsSetChatToPlayer` (the person sets the chat target, #3555) |
| The rest of the game functions of the guide | A function that reads entities (a unit, a position) can get a selector in a later ticket | Until then: the game program only |
| `abs`, `floor`, `ceil`, `round`, `xsCeilToInt` | Score operations on the fixed point value | — |
| `sqrt`, `xsVectorLength`, `xsVectorNormalize`, `dist` | An integer square root by Newton steps (a fixed number of lines) | 0.001 |
| `pow` | A literal `int` exponent: products | Another exponent: the game program only |
| `degrees`, `radians` | A product with the constant | 0.001 |
| `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `exp`, `ln`, `log2`, `log10` | None yet (a table in storage is possible later) | The game program only |
| `vector`, `xsVectorSet`, `xsVectorGetX/Y/Z`, `xsVectorSetX/Y/Z` | The three holders | — |
| The Script Call effect | The trigger function runs `function aoe2mc:xs/...` of the code of the effect | — |
| The Script Call condition | The tick line runs the function into a holder first, then tests `#r.F matches 1` | — |
| The map script, `main()` | `main()` in the first tick with a player, then the rules | — |
| The random map `#includeXS` | The same compile of the file of `--xs` (#5666) | — |
| The saved game | Minecraft saves the scores | — |

### A part with no datapack form

- The converter skips each statement that holds a part with no datapack form, and the rest of the script compiles.
  It prints one warning line per part (not per use), for example
  `XS script: sin (line 12): no datapack form, the game program runs it (game/run.py)`. This is the rule of the epic
  for an unknown name ("one warning line, and the rest of the script runs").
- A skipped function call is no command, a skipped assignment keeps the old value, and a skipped `if` or loop skips
  its body too.
- The world keeps the full script in aoe2mc.json (`"xs_script"`, #5122). The game program runs it with option A, so
  each part works there. The game program sets the score `#a aoe_xs` to 1 before the people join (as `#wait`,
  `game/run.py`): then the tick lines of B do nothing, and the script does not run two times.

### The order of the work

Each step is one sub-issue of #5119 (size S or M), in this order. The first step is useful alone: a map script
that sets the trigger variables in `main()` works in a vanilla world.

1. #5689: `int` and `bool` globals, the operators, `main()`, `xsSetTriggerVariable`, `xsTriggerVariable`, `xsChatData`;
   the warning line for all other parts; the score `#a aoe_xs` of the game program.
2. #5690: `if`, `else`, `while`, `for`, `break`, `continue`, `switch`.
3. #5691: Functions: parameters, locals, `return`, calls in expressions, `const`, `static`, `extern`; recursion gives the
   warning line.
4. #5692: Rules and the control functions; `xsGetTime`, `xsGetGameTime`.
5. #5693: The Script Call effect and condition in the datapack triggers (after #5663 and #5664).
6. #5694: `float` and `vector` as fixed point, and the math and vector functions of the table.
7. #5695: `xsGetObjectCount`, `xsGetObjectCountTotal`, `xsGetPlayerCivilization`.
8. #5696: `#includeXS` of a random map in a vanilla world (after #5666).
