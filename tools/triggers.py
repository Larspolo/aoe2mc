#!/usr/bin/env python3
"""
Count the trigger conditions and effects of scenarios and campaigns (#646, epic #645), so that the trigger tickets
do the most common types first.

Usage:
    python3 tools/triggers.py FILE...                  # .aoe2scenario, .aoe2campaign, .scx, .cpx, .cpn
    python3 tools/triggers.py --doc docs/triggers.md FILE...

Old scenarios (.scx, also inside a .cpx or .cpn) have no trigger reader yet: they count as "not read".
`--doc` writes the table of docs/triggers.md: each type, its count and the datapack command that does it (`MAP`).
"""
import argparse
import contextlib
import io
import os
import sys
import tempfile
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import aoe2mc  # noqa: E402

AREA = "`execute if entity @e[team=pN,x=..,z=..,dx=..,dz=..]`"
NO_ECONOMY = "not supported: a converted world has no resources, technologies or AI (the game program has some)"
# The datapack command of each type (Minecraft features first, CLAUDE.md), or "not supported" and why.
MAP = {
    ("condition", "TIMER"): "`schedule function ... <s>s` (one function per trigger)",
    ("condition", "OBJECTS_IN_AREA"): AREA,
    ("condition", "BRING_OBJECT_TO_OBJECT"): "`execute at @e[tag=aoe2mc.rA,limit=1] if entity @e[tag=aoe2mc.rB,distance=..T]` in the tick function: within one tile (units, #2771); a building: not supported yet",
    ("condition", "BRING_OBJECT_TO_AREA"): "`execute if entity @e[tag=aoe2mc.rN,x=..,dx=..]` in the tick function (units, #2620); a building: not supported yet",
    ("condition", "OWN_OBJECTS"): "`execute store result score ... if entity @e[tag=aoe2mc.pN]`, then `if score ... matches N..` (units only, #2573)",
    ("condition", "OWN_FEWER_OBJECTS"): "`execute store result score ... if entity @e[tag=aoe2mc.pN]`, then `if score ... matches ..N` (units only, #2573)",
    ("condition", "DESTROY_OBJECT"): "`execute unless entity @e[tag=aoe2mc.rN]` in the tick function (units, #2618); a building: not supported yet",
    ("condition", "OBJECT_ATTACKED"): "`execute if entity @e[tag=aoe2mc.rN,nbt=!{HurtTime:0s}]` in the tick function: the unit took damage from any attacker in the last 10 ticks, vanilla has no attacker in a selector (units, #2779); a building: not supported yet",
    ("condition", "CAPTURE_OBJECT"): "`execute if entity @e[tag=aoe2mc.rN,tag=aoe2mc.pN]` in the tick function (units, #2619); a building: not supported yet",
    ("condition", "DISPLAY_TIMER_TRIGGERED"): "`execute if score #doneN aoe_timer matches 1..` in the tick function: the timer sets the score at 0 (#2702)",
    ("condition", "OBJECT_HP"): "`execute store result score ... run data get entity @e[tag=aoe2mc.rN,limit=1] Health` in the tick function, then `if score ... matches` (#2701)",
    ("condition", "COMPARE_VARIABLES"): "`execute if score #vA aoe_var <op> #vB aoe_var` in the tick function, once; `unless` for not equal and inverted (#2698)",
    ("condition", "VARIABLE_VALUE"): "`execute if score #vN aoe_var matches ..` in the tick function, once (#2611)",
    ("condition", "AND"): "the default between two conditions: all conditions of one group in one `execute if ... if ...` line (#2765)",
    ("condition", "OR"): "one `execute if ... run function` line per group in the tick function, with the same fire score `#N aoe_trig`: the trigger runs once (#2765); a timer of a group: a `schedule` sets `#N.t<group> aoe_trig`, the line of the group tests it (#2791); not yet with a chance or in a disabled trigger",
    ("condition", "CHANCE"): "`execute store result score ... run random value 1..100` once per second (alone, after the timers or with the ticked conditions: #2574)",
    ("condition", "PLAYER_DEFEATED"): "`if score #pN aoe_lost matches 1..` in the tick function: the scenario mode of the game program sets the score when it defeats player N (conquest, regicide, #2710)",
    ("condition", "ACCUMULATE_ATTRIBUTE"): "`execute if score Gold aoe_resN matches Q..`: the resource scores of the game program (#2655)",
    ("condition", "RESEARCH_TECHNOLOGY"): "`if score #pN.NAME aoe_tech matches 1..` in the tick function: the scenario mode of the game program sets the score of each researched technology (#2656)",
    ("condition", "RESEARCHING_TECH"): "`if score #pN.NAME aoe_techstate matches 2` in the tick function: the scenario mode of the game program sets the AoE2 TechnologyState of the technology (#2769)",
    ("condition", "TECHNOLOGY_STATE"): "`if score #pN.NAME aoe_techstate matches Q` in the tick function: the scenario mode of the game program sets the AoE2 TechnologyState of the technology (#2769)",
    ("condition", "DIFFICULTY_LEVEL"): "`execute if score #level aoe_difficulty matches N` (the game program sets the score, #2704)",
    ("condition", "TRIGGER_ACTIVE"): "`execute if score #N aoe_on matches 1` (0 when inverted) in the tick function: the state of trigger N (#2699)",
    ("condition", "DIPLOMACY_STATE"): "`execute if score #pN.pM aoe_dipstate matches S` (the stance + 1: the scenario mode of the game program sets the score at the start and after each change, #2757)",
    ("condition", "OBJECT_HAS_ACTION"): "`execute if score #rN aoe_action matches A` (`unless` when inverted) in the tick function: the scenario mode of the game program sets the AoE2 UnitAIAction of the villager state (`scenario.ACTIONS`: build, gather, hunt, move, enter, repair, idle, #2867); another action, a target object or no unit object: not supported yet",
    ("condition", "OBJECT_NOT_VISIBLE"): "`execute if score #rN.p1 aoe_seen matches 0` in the tick function: the scenario mode of the game program sets the score from the sight of player 1 (#2756)",
    ("condition", "OBJECT_VISIBLE"): "`execute if score #rN.p1 aoe_seen matches 1` in the tick function: the scenario mode of the game program sets the score from the sight of player 1 (#2756)",
    ("condition", "OBJECT_VISIBLE_MULTIPLAYER"): "`execute if score #rN.pM aoe_seen matches 1` in the tick function: the scenario mode of the game program sets the score from the sight of player M (#2756)",
    ("condition", "VICTORY_TIMER"): "`execute if score #pN.T aoe_vic matches ..` in the tick function: the scenario mode of the game program sets the years left on the wonder (T 0), relic (1) or King of the Hill (2) timer of player N and resets the score when the timer stops (#2906); inverted: not supported yet",
    ("condition", "UNITS_GARRISONED"): "`if score #gREF aoe_gar matches N..` in the tick function: the scenario mode of the game program sets the number of units inside each converted building (#2714); a transport ship: not supported yet",
    ("condition", "OBJECT_SELECTED"): "not supported: Minecraft has no selection",
    ("condition", "OBJECT_SELECTED_MULTIPLAYER"): "not supported: Minecraft has no selection",
    ("condition", "OBJECT_HAS_TARGET"): "not supported: Minecraft has no readable target of a mob",
    ("condition", "AI_SIGNAL"): "not supported: the bots of the game program run no AI script",
    ("condition", "AI_SIGNAL_MULTIPLAYER"): "not supported: the bots of the game program run no AI script",
    ("condition", "SCRIPT_CALL"): "not supported: no XS scripts",
    ("condition", "LOCAL_TECH_RESEARCHED"): "not supported: Chronicles only, the game program has no local technologies",
    ("condition", "HERO_POWER_CAST"): "not supported: Chronicles only, the game program has no hero powers",
    ("effect", "SEND_CHAT"): "`tellraw @a[team=pN] {\"text\": ...}`",
    ("effect", "DISPLAY_INSTRUCTIONS"): "`title @a actionbar` (short text) or `title @a subtitle`",
    ("effect", "CLEAR_INSTRUCTIONS"): "`title @a clear` (#2609)",
    ("effect", "CLEAR_TIMER"): "`bossbar remove aoe2mc:timerN` and `schedule clear aoe2mc:timer/N` of the slot N (#2696)",
    ("effect", "CREATE_GARRISONED_OBJECT"): "`summon` of the unit (`units.make_entity()`) in the state of a garrisoned unit (`Invulnerable`, `NoAI`, tags `aoe2mc.garrisoned`, `aoe2mc.made_inside`) on the inside cells of each selected building; the game program adds it to the garrison (#2764); a ship or ram holder: not supported yet",
    ("effect", "CREATE_OBJECT"): "`summon` of the entity of `units.make_entity()` (units, timer triggers: #656); a building: the order `create` of the scenario mode, a complete building (#2911)",
    ("effect", "CREATE_OBJECT_ARMOR"): "the change \"N NAME melee 2 V\" or \"N NAME pierce 2 V\" in the storage `aoe2mc:attributes` (an add, as AoE2 adds the entries of one class): the scenario mode of the game program adds V to the melee or pierce armor of the unit type of the player (`train.stats`, #2855); the other armor classes are not supported",
    ("effect", "CREATE_OBJECT_ATTACK"): "the change \"N NAME attack 2 V\" in the storage `aoe2mc:attributes` for the attack classes 3 and 4: the scenario mode of the game program adds V to the attack of the unit type of the player (`train.stats`, #2855); the bonus classes are not supported",
    ("effect", "REMOVE_OBJECT"): "`kill @e[tag=aoe2mc.pN,type=..,x=..,y=..,z=..,dx=..,dy=..,dz=..]` (timer triggers: #656)",
    ("effect", "REPLACE_OBJECT"): "`tag` of the old units, `execute at` each one `run summon` of the new entity of the target player (`units.make_entity()`), then `kill` of the old units and their mounts (#2703); buildings: not supported yet",
    ("effect", "KILL_OBJECT"): "`kill @e[tag=aoe2mc.pN,type=..,x=..,y=..,z=..,dx=..,dy=..,dz=..]`, no area: the whole map (#2568)",
    ("effect", "DAMAGE_OBJECT"): "`execute as @e[tag=aoe2mc.pN,type=..,x=..,dx=..] run damage @s N` (N in AoE2 hit points; timer and area triggers: #2571); a negative N heals with the commands of `HEAL_OBJECT` (#2907); a building: not supported yet",
    ("effect", "HEAL_OBJECT"): "`execute as @e[tag=aoe2mc.pN,type=..,x=..,dx=..] store result score` of Health and max_health, `scoreboard players add`, then `store result entity @s Health` (AoE2 hit points, not above the maximum, #2692)",
    ("effect", "INITIATE_RESEARCH"): "the order `research <ref> <technology>` in the storage `aoe2mc:orders`: the scenario mode of the game program starts it at the selected building as a click of its menu, and the player pays (#2772)",
    ("effect", "TELEPORT_OBJECT"): "`tp @e[tag=aoe2mc.pN,x=..,dx=..] x y z` and the mounts of the riders (#2569)",
    ("effect", "TRAIN_UNIT"): "the order `train <ref> <unit> <quantity>` in the storage `aoe2mc:orders`: the scenario mode of the game program queues the units at the selected building as clicks of its menu, and the player pays (#2772)",
    ("effect", "CHANGE_OBJECT_ARMOR"): "`execute as @e[tag=aoe2mc.pN,type=..,x=..,dx=..] run attribute @s minecraft:armor modifier add aoe2mc:trig_N_I V add_value` (add: V = N, subtract: V = -N, #2755); set: `modifier remove` of the earlier add and subtract effects, then `attribute @s minecraft:armor base set N` (#2909)",
    ("effect", "CHANGE_OBJECT_ATTACK"): "`execute as @e[tag=aoe2mc.pN,type=..,x=..,dx=..] run attribute @s minecraft:attack_damage modifier add aoe2mc:trig_N_I V add_value` for the attack classes 3 and 4 (add and subtract, #2755); set: `modifier remove` of the earlier add and subtract effects, then `attribute @s minecraft:attack_damage base set N` (#2909)",
    ("effect", "CHANGE_PLAYER_NAME"): "`team modify pN displayName {\"text\": \"...\"}`: the sidebar and the tab list (#2711)",
    ("effect", "CHANGE_OBJECT_NAME"): "`execute as @e[tag=aoe2mc.pN,type=..,x=..,dx=..] run data modify entity @s CustomName.text set value \"...\"` (the player color stays, #2616)",
    ("effect", "CHANGE_OBJECT_HP"): "`attribute ... minecraft:max_health base set N` (AoE2 hit points, 1 to 1024); add, subtract, multiply, divide: the function `hp/<op>_<N>` reads the base into the score #hp of aoe_hp and sets it with the macro `hp/apply` (#2693)",
    ("effect", "CHANGE_OWNERSHIP"): "`tag` `aoe2mc.pN` and `team join pN` of the units in the area and their mounts (timer and area triggers: #2570); to Gaia: `tag remove` and `team leave` (#2908); from Gaia: not supported yet",
    ("effect", "CHANGE_OBJECT_SPEED"): "`attribute @e[..] minecraft:movement_speed base set V` of the units in the area and their mounts, V from the walk speed of the game program (game/ai.py, #2694)",
    ("effect", "DISABLE_OBJECT_SELECTION"): "`tag @e[..] add aoe2mc.unselectable` of the units of the player in the area: no click, selection box or double click of the game program selects them (#2854)",
    ("effect", "ENABLE_OBJECT_SELECTION"): "`tag @e[..] remove aoe2mc.unselectable` of the units of the player in the area (#2854)",
    ("effect", "MODIFY_OBJECT_ATTRIBUTE"): "the commands of the effect of the attribute on the units of the player in the area: hit points as Change Object HP, a set of the speed as Change Object Speed, armor and attack as Change Object Armor and Attack (`attribute ... modifier add`); another attribute: not supported (#2860)",
    ("effect", "DISABLE_UNIT_ATTACKABLE"): "`data merge entity @s {Invulnerable:1b}` of the units of the player in the area (#2695)",
    ("effect", "ENABLE_UNIT_ATTACKABLE"): "`data merge entity @s {Invulnerable:0b}` of the units in the area, not the garrisoned ones (#2695)",
    ("effect", "DISABLE_UNIT_TARGETING"): "`tag @e[..] add aoe2mc.notarget` of the units of the player in the area: no unit or tower chooses them as a target, an attack order still hits (#2826)",
    ("effect", "ENABLE_UNIT_TARGETING"): "`tag @e[..] remove aoe2mc.notarget` of the units of the player in the area (#2826)",
    ("effect", "FREEZE_OBJECT"): "`data merge entity @s {NoAI:1b}` of the units in the area and their mounts (#2608)",
    ("effect", "CHANGE_OBJECT_VISIBILITY"): "`effect give @s minecraft:invisibility infinite 0 true` (or `effect clear`) of the selected units, the units in the area and their mounts, and `CustomNameVisible` of the name tag; all players see it, Minecraft cannot hide an entity from one player only (#2862)",
    ("effect", "CHANGE_VIEW"): "`tp @a[team=pN] x y z` to the tile, on the ground (the player is the camera, #2610)",
    ("effect", "PLAY_SOUND"): "`playsound` of the vanilla sound of the name part (`data/sounds.jsonl`), at the tile or at each player (#2644)",
    ("effect", "DISPLAY_TIMER"): "`bossbar` aoe2mc:timerN and a `schedule function` each second with the time left (timer and area triggers: #2572)",
    ("effect", "ACTIVATE_TRIGGER"): "`scoreboard players set #<trigger> aoe_on 1` and the `schedule` of its timer (timer and area triggers: #2575)",
    ("effect", "DEACTIVATE_TRIGGER"): "`scoreboard players set #<trigger> aoe_on 0` and `schedule clear` of its timer (#2575)",
    ("effect", "CHANGE_VARIABLE"): "`scoreboard players set`, `add`, `remove` or `operation` on `#vN aoe_var` (#2611)",
    ("effect", "STORE_KEY_VALUE"): "`execute store result storage aoe2mc:keys values.\"<key>\" int 1 run scoreboard players get #vN aoe_var` (#2887); AoE2 keeps the keys between the scenarios of a campaign, a converted world keeps them only in the world",
    ("effect", "LOAD_KEY_VALUE"): "`scoreboard players set #vN aoe_var <quantity>`, then `execute if data storage aoe2mc:keys values.\"<key>\" store result score #vN aoe_var run data get ...` (#2887); the keys stay only in the world, not between the scenarios of a campaign",
    ("effect", "DELETE_KEY"): "`data remove storage aoe2mc:keys values.\"<key>\"` (#2887); the keys stay only in the world, not between the scenarios of a campaign",
    ("effect", "MODIFY_VARIABLE_BY_ATTRIBUTE"): "the request in the storage `aoe2mc:reads`: the scenario mode of the game program runs `scoreboard players operation #vN aoe_var = #read aoe_var` (or `+=`, `-=`, `*=`, `/=`) with the hit points, attack, melee and pierce armor, range or reload of the unit type of the player (`train.stats`, #2858)",
    ("effect", "MODIFY_VARIABLE_BY_RESOURCE"): "`scoreboard players operation #vN aoe_var = Gold aoe_resP` (or `+=`, `-=`, `*=`, `/=`): the stock of the game program, `aoe_res` for player 1 (#2823)",
    ("effect", "MODIFY_VARIABLE_BY_VARIABLE"): "`scoreboard players operation #vA aoe_var = #vB aoe_var` (or `+=`, `-=`, `*=`, `/=`, #2713); a division by 0 leaves the score as it is (Minecraft; the AoE2 wiki has no page on it)",
    ("effect", "COUNT_UNITS_INTO_VARIABLE"): "`execute store result score #vN aoe_var if entity @e[tag=aoe2mc.pM,type=..,x=..,dx=..]`: the number of units of the player in the area, no area: the whole map (#2697)",
    ("effect", "DECLARE_VICTORY"): "`scoreboard players set #pN aoe_win 1`: the scenario mode of the game program ends the game (#2542)",
    ("effect", "TASK_OBJECT"): "`tag @e[tag=aoe2mc.pN,x=..,dx=..] add aoe_taskK` and the tile in the storage `aoe2mc:tasks`: the scenario mode of the game program walks them there with `aoe moveto` (vanilla has no walk-to command, #2646)",
    ("effect", "PATROL"): "`tag` of the units in the area and an order in the storage `aoe2mc:orders`: the scenario mode of the game program walks them with `aoe moveto` (#2647); vanilla has no walk-to command",
    ("effect", "ATTACK_MOVE"): "`tag` of the units in the area and an order in the storage `aoe2mc:orders`: the scenario mode of the game program gives them the aggressive stance and `aoe moveto` (#2647); vanilla has no walk-to command",
    ("effect", "LOCK_GATE"): "the order `lock <ref>` in the storage `aoe2mc:orders`: the scenario mode of the game program puts the portcullis on the gate and locks it with `aoe gate lock X Z` (the bars stay down, #2762)",
    ("effect", "UNLOCK_GATE"): "the order `unlock <ref>` in the storage `aoe2mc:orders`: the scenario mode of the game program unlocks the gate with `aoe gate unlock X Z` (#2762)",
    ("effect", "STOP_OBJECT"): "`tag` of the units in the area and the order `stop <tag>` in the storage `aoe2mc:orders`: the scenario mode of the game program stops them with `aoe stop` and ends their patrols (#2754); vanilla has no stop of a walk order",
    ("effect", "PLACE_FOUNDATION"): "the order `found <player> <building> <x> <y>` in the storage `aoe2mc:orders`: the scenario mode of the game program puts the construction site of the building for free at the tile when the place is free (`build.found`, #2825)",
    ("effect", "BUILD_OBJECT"): "the order `build <player> <building> <x1> <y1> <x2> <y2>` in the storage `aoe2mc:orders`: the scenario mode of the game program completes the construction sites of the player in the area at once, with no villager work (`build.rise`, #2863)",
    ("effect", "CHANGE_OBJECT_RANGE"): "`tag` of the units in the area and the order `range <tag> <operation> <quantity>` in the storage `aoe2mc:orders`: the scenario mode of the game program sends the new range of each tagged ranged unit with `aoe range` (#2767); vanilla has no shot range",
    ("effect", "UNLOAD"): "the order `unload <player> <ref>` of each selected building (or each building in the area) in the storage `aoe2mc:orders`: the scenario mode of the game program lets its garrison out and walks it to the tile with `aoe moveto` (#2773); a ship or ram holder: not supported yet",
    ("effect", "CHANGE_OBJECT_STANCE"): "`tag` of the units in the area and an order in the storage `aoe2mc:orders`: the scenario mode of the game program sets the stance with `aoe stance` (#2705); vanilla has no stance",
    ("effect", "TRIBUTE"): "`scoreboard players add`/`remove` on `#pN.<resource> aoe_res`; the game program puts it into the stock (`--mode scenario`: `scenario.resources`, #2576)",
    ("effect", "MODIFY_RESOURCE"): "`scoreboard players add`/`remove` on `#pN.<resource> aoe_res`, a set on `aoe_set`; the game program puts it into the stock (`--mode scenario`: `scenario.resources`, #2576)",
    ("effect", "MODIFY_RESOURCE_BY_VARIABLE"): "`scoreboard players operation #pN.<resource> aoe_res += or -= #vM aoe_var`, a set is `operation = #vM aoe_var` on `aoe_set`; add, subtract and set only, multiply and divide are not supported (#2768)",
    ("effect", "CHANGE_TECHNOLOGY_RESEARCH_TIME"): "the time in the storage `aoe2mc:times`: the scenario mode of the game program uses it when the player researches the technology (`train.seconds`, #2820)",
    ("effect", "CHANGE_OBJECT_COST"): "the cost in the storage `aoe2mc:costs`: the scenario mode of the game program uses it in the menus and when the player pays (#2776)",
    ("effect", "CHANGE_TECHNOLOGY_COST"): "the cost of the technology in the storage `aoe2mc:costs`: the scenario mode of the game program uses it in the menus and when the player pays (#2819)",
    ("effect", "CHANGE_TECHNOLOGY_LOCATION"): "`data modify storage aoe2mc:places list append value \"<player> <technology> <building> <button>\"`: the scenario mode of the game program moves the item to the menu of the building, at the slot of the AoE2 button (#2864)",
    ("effect", "CHANGE_TRAIN_LOCATION"): "`data modify storage aoe2mc:places list append value \"<player> <unit> <building> <button>\"`: the scenario mode of the game program moves the item to the menu of the building, at the slot of the AoE2 button (#2864)",
    ("effect", "CHANGE_CIVILIZATION_NAME"): "`data modify storage aoe2mc:names civs append value \"<player> <name>\"`: the scenario mode of the game program shows the name next to the player name in the player list and the diplomacy page (#2905); a name of the game files only (`string_id`): not supported",
    ("effect", "CHANGE_TECHNOLOGY_NAME"): "`data modify storage aoe2mc:names list append value \"<player> <technology> <name>\"`: the scenario mode of the game program shows the name in the menus of the player (#2821); a name of the game files only (`string_id`): not supported",
    ("effect", "ADD_TRAIN_LOCATION"): "`data modify storage aoe2mc:locations list append value \"<player> <unit> <building> <button> <seconds>\"`: the scenario mode of the game program adds the unit to the menu of the building of the player, at the button with the train time (#2865); the hotkey: not supported",
    ("effect", "MODIFY_ATTRIBUTE_FOR_CLASS"): "one change for the class `@<ObjectClass>` in the storage `aoe2mc:attributes`: the scenario mode of the game program changes the values of each unit type of the class (`train.applies`, `train.CLASSES`: archer, cavalry, cavalry archer, hand cannoneer, infantry, siege weapon, spearman, war elephant, warship; #2859); the other classes are not supported",
    ("effect", "MODIFY_ATTRIBUTE"): "the change in the storage `aoe2mc:attributes`: the scenario mode of the game program changes the hit points, attack, melee and pierce armor, range or reload of the unit type of the player (`train.stats`, #2763); the other attributes are not supported",
    ("effect", "MODIFY_ATTRIBUTE_BY_VARIABLE"): "the score `#vN aoe_var` goes with `execute store result storage` and a macro function into the line of the storage `aoe2mc:attributes`; the scenario mode of the game program changes the values as for Modify Attribute (#2856)",
    ("effect", "ENABLE_DISABLE_OBJECT"): "the item in the storage `aoe2mc:menus`: the scenario mode of the game program shows or hides it in the menus of the player (#2775)",
    ("effect", "ENABLE_DISABLE_TECHNOLOGY"): "the technology in the storage `aoe2mc:menus`: the scenario mode of the game program shows or hides it in the menus of the player (#2775)",
    ("effect", "RESEARCH_TECHNOLOGY"): "`scoreboard players set #rN.I aoe_tech 1`: the scenario mode of the game program gives the technology (#2577)",
    ("effect", "CHANGE_COLOR_MOOD"): "`time set` and `weather` of the mood (`MOODS`, `RAIN`; timer and area triggers: #1876); the fog stays",
    ("effect", "CHANGE_OBJECT_PLAYER_COLOR"): "`execute as @e[tag=aoe2mc.pN,type=..,x=..,dx=..] run data modify entity @s CustomName.color set value \"<color>\"`: the name gets the hex color of the player color (`units.HEX`, as the converted names); the owner, the team and the glow stay (#2824)",
    ("effect", "CHANGE_PLAYER_COLOR"): "`team modify pN color`: the chat color of the new player color (`units.TEAM_COLOR`) on the names and the glow of the units; the wool of the sheep and the banners keep the old color (#2712)",
    ("effect", "CHANGE_DIPLOMACY"): "`scoreboard players set #pN.pM aoe_dip`: the scenario mode of the game program changes the stance (#2645)",
    ("effect", "MIRROR_DIPLOMACY"): "`scoreboard players set #mN.pM aoe_dip`: the scenario mode of the game program gives player N the stances of player M toward each other player (#2822)",
    ("effect", "SET_PLAYER_VISIBILITY"): "`scoreboard players set #pN.pM aoe_vis`: the scenario mode of the game program shows the units of player M to player N out of sight, or hides them again (`fog.py`, #2774)",
    ("effect", "CHANGE_OBJECT_ICON"): "not supported: an icon of the AoE2 interface only",
    ("effect", "CHANGE_OBJECT_DESCRIPTION"): "not supported: a text of the AoE2 interface only",
    ("effect", "CHANGE_OBJECT_CAPTION"): "not supported: a text of the AoE2 interface only",
    ("effect", "CHANGE_OBJECT_PLAYER_NAME"): "not supported: the game program shows no player name of a unit",
    ("effect", "CHANGE_OBJECT_CIVILIZATION_NAME"): "not supported: the game program shows no civilization name of a unit",
    ("effect", "CHANGE_TECHNOLOGY_DESCRIPTION"): "not supported: a text of the AoE2 interface only",
    ("effect", "CHANGE_TECHNOLOGY_ICON"): "not supported: an icon of the AoE2 interface only",
    ("effect", "CHANGE_TECHNOLOGY_HOTKEY"): "not supported: Minecraft has no hotkeys of the menus",
    ("effect", "USE_ADVANCED_BUTTONS"): "not supported: a setting of the AoE2 interface only",
    ("effect", "AI_SCRIPT_GOAL"): "not supported: the bots of the game program run no AI script",
    ("effect", "ACKNOWLEDGE_AI_SIGNAL"): "not supported: the bots of the game program run no AI script",
    ("effect", "ACKNOWLEDGE_MULTIPLAYER_AI_SIGNAL"): "not supported: the bots of the game program run no AI script",
    ("effect", "SCRIPT_CALL"): "not supported: no XS scripts",
    ("effect", "ENABLE_OBJECT_DELETION"): "not supported: the game program has no delete order",
    ("effect", "DISABLE_OBJECT_DELETION"): "not supported: the game program has no delete order",
    ("effect", "RESEARCH_LOCAL_TECHNOLOGY"): "not supported: Chronicles only, the game program has no local technologies",
}


def scenario_types(path):
    """Counter of (kind, type name) of one .aoe2scenario file."""
    from AoE2ScenarioParser.datasets.conditions import ConditionId
    from AoE2ScenarioParser.datasets.effects import EffectId
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

    def name(enum, v):
        try:
            return enum(v).name
        except ValueError:
            return f"UNKNOWN_{v}"
    with contextlib.redirect_stdout(io.StringIO()):     # the parser prints a lot of status text
        scn = AoE2DEScenario.from_file(str(path))
    n = Counter()
    for t in scn.trigger_manager.triggers:
        n.update(("condition", name(ConditionId, c.condition_type)) for c in t.conditions)
        n.update(("effect", name(EffectId, e.effect_type)) for e in t.effects)
    return n


def count(path):
    """Counter of (kind, type name) of a scenario or campaign. An old scenario counts as ("not read", ".scx")."""
    ext = os.path.splitext(str(path))[1].lower()
    if ext == ".aoe2scenario":
        return scenario_types(path)
    if ext in (".aoe2campaign", ".cpx", ".cpn"):
        n = Counter()
        with tempfile.TemporaryDirectory() as tmp:
            for i, (title, data) in enumerate(aoe2mc.read_campaign(path)[2]):
                sub = os.path.join(tmp, f"{i}{os.path.splitext(title)[1].lower()}")
                with open(sub, "wb") as f:
                    f.write(data)
                n += count(sub)
        return n
    return Counter({("not read", ext): 1})


def table(n):
    """The Markdown table of docs/triggers.md: the counted types and the types of MAP, the most common first."""
    rows = sorted(set(n) | set(MAP), key=lambda k: (-n[k], k))
    out = ["| Kind | Type | Count | Datapack command |", "|---|---|---|---|"]
    out += [f"| {k} | `{t}` | {n[(k, t)]} | {MAP.get((k, t), 'not supported: no ticket yet')} |" for k, t in rows]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--doc", help="write the Markdown table of the types into this file")
    a = ap.parse_args()
    each = {f: count(f) for f in a.files}
    n = sum(each.values(), Counter())
    for (kind, t), c in sorted(n.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{c:4d}  {kind:9s}  {t}")
    if a.doc:
        def names(files):
            return ", ".join(f"`{os.path.basename(f)}`" for f in files) or "none"
        with open(a.doc, "w") as f:
            f.write(f"# Scenario triggers\n\nGenerated by `python3 tools/triggers.py --doc {a.doc} FILE...` (#646). "
                    f"Edit `MAP` in `tools/triggers.py`, not this table.\n\n"
                    f"- Files with triggers: {names([k for k, v in each.items() if v])}.\n"
                    f"- Files without triggers: {names([k for k, v in each.items() if not v])}.\n\n{table(n)}\n")


if __name__ == "__main__":
    main()
