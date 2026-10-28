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
    ("condition", "BRING_OBJECT_TO_AREA"): "`execute if entity @e[tag=ref-N,x=..,dx=..]` (tag of the object)",
    ("condition", "OWN_OBJECTS"): "`execute store result score ... if entity @e[tag=aoe2mc.pN]`, then `if score ... matches N..` (units only, #2573)",
    ("condition", "OWN_FEWER_OBJECTS"): "`execute store result score ... if entity @e[tag=aoe2mc.pN]`, then `if score ... matches ..N` (units only, #2573)",
    ("condition", "DESTROY_OBJECT"): "`execute unless entity @e[tag=ref-N]`",
    ("condition", "CAPTURE_OBJECT"): "`execute if entity @e[tag=ref-N,team=pN]`",
    ("condition", "VARIABLE_VALUE"): "`execute if score #vN aoe_var matches ..` in the tick function, once (#2611)",
    ("condition", "CHANCE"): "`execute store result score ... run random value 1..100`",
    ("condition", "PLAYER_DEFEATED"): "`execute unless entity @e[team=pN]`",
    ("condition", "ACCUMULATE_ATTRIBUTE"): NO_ECONOMY,
    ("condition", "RESEARCH_TECHNOLOGY"): NO_ECONOMY,
    ("condition", "OBJECT_SELECTED"): "not supported: Minecraft has no selection",
    ("effect", "SEND_CHAT"): "`tellraw @a[team=pN] {\"text\": ...}`",
    ("effect", "DISPLAY_INSTRUCTIONS"): "`title @a actionbar` (short text) or `title @a subtitle`",
    ("effect", "CLEAR_INSTRUCTIONS"): "`title @a clear` (#2609)",
    ("effect", "CREATE_OBJECT"): "`summon` of the entity of `units.make_entity()` (units, timer triggers: #656); buildings: not supported yet",
    ("effect", "REMOVE_OBJECT"): "`kill @e[tag=aoe2mc.pN,type=..,x=..,y=..,z=..,dx=..,dy=..,dz=..]` (timer triggers: #656)",
    ("effect", "KILL_OBJECT"): "`kill @e[tag=aoe2mc.pN,type=..,x=..,y=..,z=..,dx=..,dy=..,dz=..]`, no area: the whole map (#2568)",
    ("effect", "DAMAGE_OBJECT"): "`execute as @e[tag=aoe2mc.pN,type=..,x=..,dx=..] run damage @s N` (N in AoE2 hit points; timer and area triggers: #2571); heal: not supported yet",
    ("effect", "TELEPORT_OBJECT"): "`tp @e[tag=aoe2mc.pN,x=..,dx=..] x y z` and the mounts of the riders (#2569)",
    ("effect", "CHANGE_OBJECT_NAME"): "`execute as @e[tag=aoe2mc.pN,type=..,x=..,dx=..] run data modify entity @s CustomName.text set value \"...\"` (the player color stays, #2616)",
    ("effect", "CHANGE_OWNERSHIP"): "`tag` `aoe2mc.pN` and `team join pN` of the units in the area and their mounts (timer and area triggers: #2570); Gaia: not supported yet",
    ("effect", "FREEZE_OBJECT"): "`data merge entity @s {NoAI:1b}` of the units in the area and their mounts (#2608)",
    ("effect", "CHANGE_VIEW"): "`tp @a[team=pN] x y z` to the tile, on the ground (the player is the camera, #2610)",
    ("effect", "PLAY_SOUND"): "`playsound` of the vanilla sound of the name part (`data/sounds.jsonl`), at the tile or at each player (#2644)",
    ("effect", "DISPLAY_TIMER"): "`bossbar` aoe2mc:timerN and a `schedule function` each second with the time left (timer and area triggers: #2572)",
    ("effect", "ACTIVATE_TRIGGER"): "`scoreboard players set <trigger> aoe_trig 1`",
    ("effect", "DEACTIVATE_TRIGGER"): "`scoreboard players set <trigger> aoe_trig 0`",
    ("effect", "CHANGE_VARIABLE"): "`scoreboard players set`, `add`, `remove` or `operation` on `#vN aoe_var` (#2611)",
    ("effect", "DECLARE_VICTORY"): "`scoreboard players set #pN aoe_win 1`: the scenario mode of the game program ends the game (#2542)",
    ("effect", "TASK_OBJECT"): "not supported: vanilla has no walk-to command (the game program: `aoe moveto`)",
    ("effect", "PATROL"): "not supported: vanilla has no walk-to command",
    ("effect", "ATTACK_MOVE"): "not supported: vanilla has no walk-to command",
    ("effect", "TRIBUTE"): NO_ECONOMY,
    ("effect", "MODIFY_RESOURCE"): NO_ECONOMY,
    ("effect", "RESEARCH_TECHNOLOGY"): "`scoreboard players set #rN.I aoe_tech 1`: the scenario mode of the game program gives the technology (#2577)",
    ("effect", "CHANGE_COLOR_MOOD"): "`time set` and `weather` of the mood (`MOODS`, `RAIN`; timer and area triggers: #1876); the fog stays",
    ("effect", "CHANGE_DIPLOMACY"): "not supported: the teams of a world do not fight by themselves",
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
