#!/usr/bin/env python3
"""Compare the AoE2 values of the data files with the .dat of an installed AoE2 DE game (#5245).

Usage: python3 tools/dat_compare.py [PATH/empires2_x2_p1.dat]

Prints one line for each difference ("NAME key: data value, game value"). Exit 0: no difference, 1: differences,
2: no .dat or no genieutils-py. The rules of the compare: ticket #5245 (epic #5236). When the .dat and the AoE2 wiki
do not agree, the .dat wins (docs/research/gameplay.md).
"""
import copy
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/AoE2DE/AgeOfEmpires2Data/"
                             "resources/_common/dat/empires2_x2_p1.dat")
# The free effects of each age (rule 2): an age value of a unit is also correct.
AGES = ((101, 90, 72, 16), (102, 71, 511, 799), (103, 821))
# Rule 3: the attributes of the effect commands.
HP, SIGHT, ARMOR, ATTACK, RELOAD, RANGE, TRAIN_TIME = 0, 1, 8, 9, 10, 12, 101
# Rule 4: the armor classes; class 31 is on all units with 0.
CLASSES = {1: "infantry", 3: "pierce", 4: "melee", 5: "elephant", 8: "cavalry", 11: "building", 13: "stone", 15: "archer",
           16: "ship", 17: "ram", 19: "unique", 20: "siege", 21: "standard", 22: "wall", 23: "gunpowder", 25: "monk",
           26: "castle", 27: "spearman", 28: "cavalry archer", 29: "eagle", 30: "camel", 32: "condottiero", 35: "mameluke",
           37: "heavysiege", 38: "skirmisher", 41: "fireship", 60: "warship"}
IGNORE_CLASS = 31
VILLAGER = 118                                  # rule 5: the train location of a placed building
GATES = {"GATE": 63, "PALISADE_GATE": 64}       # rule 5: the segment units, not the placement units 487, 488
RESOURCES = {0: "food", 1: "wood", 2: "stone", 3: "gold"}
# The villager unit of each gather kind of gather.AOE2_WORK (the oyster: no own unit).
GATHERERS = {"farm": 214, "fish": 56, "food": 120, "gold": 579, "hunt": 122, "stone": 124, "wood": 123}


def rows(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def most_common(values):
    """Rule 1: the base value is the most common value over all civilizations."""
    values = [v for v in values if v is not None]
    return Counter(values).most_common(1)[0][0] if values else None


def base_unit(dat, uid):
    """The unit of the most common civilization variant (rule 1): the unit of the first civilization (no Gaia) whose
    hit points, attack and armor are the most common ones."""
    units = [c.units[uid] for c in dat.civs[1:] if uid < len(c.units) and c.units[uid] is not None]
    if not units:
        return None
    key = Counter(json.dumps(stats(u), sort_keys=True) for u in units).most_common(1)[0][0]
    return next(u for u in units if json.dumps(stats(u), sort_keys=True) == key)


def pairs(lst):
    return {a.class_: a.amount for a in lst or ()}


def stats(u):
    """The values of unit u in the form of units.jsonl."""
    t = u.type_50
    atk, arm = pairs(t.attacks if t else ()), pairs(t.armours if t else ())
    d = {"hp": u.hit_points, "sight": round(u.line_of_sight)}
    if t:
        d |= {"attack": max(atk.get(4, 0), atk.get(3, 0)), "melee": arm.get(4, 0), "pierce": arm.get(3, 0),
              "range": round(t.max_range), "reload": round(t.reload_time, 3),
              "bonus": {CLASSES[c]: a for c, a in sorted(atk.items()) if c in CLASSES and c not in (3, 4) and a}}
    if u.speed:
        d["walk"] = round(u.speed, 3)
    return d


def apply(u, effect):
    """Apply the unit commands of an effect to unit u in place (rule 3)."""
    for c in effect.effect_commands:
        if c.type not in (0, 4, 5) or not (c.a == u.id or (c.a == -1 and c.b == u.class_)):
            continue
        op = {0: lambda old, v: v, 4: lambda old, v: old + v, 5: lambda old, v: old * v}[c.type]
        if c.c == HP:
            u.hit_points = op(u.hit_points, c.d)
        elif c.c == SIGHT:
            u.line_of_sight = op(u.line_of_sight, c.d)
        elif c.c in (ARMOR, ATTACK) and u.type_50:
            cls, v = divmod(int(c.d), 256)
            lst = u.type_50.armours if c.c == ARMOR else u.type_50.attacks
            hit = next((a for a in lst if a.class_ == cls), None)
            if hit:
                hit.amount = op(hit.amount, v)
        elif c.c == RELOAD and u.type_50:
            u.type_50.reload_time = op(u.type_50.reload_time, c.d)
        elif c.c == RANGE and u.type_50:
            u.type_50.max_range = op(u.type_50.max_range, c.d)
        elif c.c == TRAIN_TIME and u.creatable:
            for loc in u.creatable.train_locations:
                loc.train_time = op(loc.train_time, c.d)


def variants(dat, u):
    """Unit u in each age (rule 2) and with each civilization technology (rule 7)."""
    out, cur = [u], copy.deepcopy(u)
    for age in AGES:
        for e in age:
            if e < len(dat.effects):
                apply(cur, dat.effects[e])
        out.append(copy.deepcopy(cur))
    for t in dat.techs:
        if getattr(t, "civ", 0) > 0 and 0 <= t.effect_id < len(dat.effects):
            v = copy.deepcopy(u)
            apply(v, dat.effects[t.effect_id])
            out.append(v)
    return out


def same(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < 0.01
    return a == b


def compare_unit(name, data, dat, uid):
    """The difference lines of one row of units.jsonl or buildings.jsonl (keys of the row only)."""
    u = base_unit(dat, uid)
    if u is None:
        return [f"{name}: no unit {uid} in the .dat"]
    found = [stats(v) for v in variants(dat, u)]
    out = []
    for k in ("hp", "attack", "melee", "pierce", "range", "reload", "sight", "walk"):
        if k in data and k in found[0] and not any(same(data[k], f.get(k)) for f in found):
            out.append(f"{name} {k}: {data[k]}, {found[0][k]}")
    if "bonus" in data and "bonus" in found[0] and not any(data["bonus"] == f.get("bonus") for f in found):
        out.append(f"{name} bonus: {data['bonus']}, {found[0]['bonus']}")
    return out


def cost(costs):
    """Rule 6: a cost with flag 0 is not paid."""
    return {RESOURCES[c.type]: c.amount for c in costs if c.flag and c.amount and c.type in RESOURCES}


def compare_cost(name, data, game_cost, game_time, times=()):
    out = []
    if "cost" in data and data["cost"] != game_cost:
        out.append(f"{name} cost: {data['cost']}, {game_cost}")
    if "time" in data and game_time is not None and not any(same(data["time"], t) for t in (game_time, *times)):
        out.append(f"{name} time: {data['time']}, {game_time}")
    return out


def train_time(u):
    locs = u.creatable.train_locations if u.creatable else []
    return locs[0].train_time if locs else None


def compare_trained(name, data, dat, uid):
    u = base_unit(dat, uid)
    if u is None or not u.creatable:
        return [f"{name}: no unit {uid} in the .dat"]
    return compare_cost(name, data, cost(u.creatable.resource_costs), train_time(u),
                        [train_time(v) for v in variants(dat, u)])


def compare_tech(name, data, dat, tid):
    if tid >= len(dat.techs):
        return [f"{name}: no technology {tid} in the .dat"]
    t = dat.techs[tid]
    locs = getattr(t, "research_locations", None) or []
    return compare_cost(name, data, cost(t.resource_costs), locs[0].research_time if locs else None)


def placed(dat, uid):
    """Rule 5: the building unit that villagers place (train location 118) of the same name, else uid."""
    u = base_unit(dat, uid)
    if u is None or (u.creatable and any(loc.unit_id == VILLAGER for loc in u.creatable.train_locations)):
        return uid
    for c in dat.civs[1:2]:
        for v in c.units:
            if v is not None and v.name == u.name and v.creatable and any(
                    loc.unit_id == VILLAGER for loc in v.creatable.train_locations):
                return v.id
    return uid


def work_rate(u):
    rates = [t.work_value_1 for t in (u.bird.tasks if u.bird else ()) if t.action_type == 5]
    return max(rates) if rates else (u.bird.work_rate if u.bird else None)


def compare(dat, units, techs, tables):
    """All difference lines. units: {name: unit ID}, techs: {name: tech ID}; tables: {file: rows}, with the gather
    rates as the rows of "AOE2_WORK"."""
    out = []
    uid = lambda n: GATES.get(n, units.get(n))
    for f in ("units.jsonl", "buildings.jsonl", "replay.jsonl"):
        for r in tables.get(f, ()):
            i = uid(r["name"])
            if i is not None:
                out += compare_unit(r["name"], {"walk": r["walk"]} if "walk" in r else r, dat, i)
    for f in ("train.jsonl", "build.jsonl"):
        for r in tables.get(f, ()):
            n = r["name"]
            if f == "build.jsonl" and uid(n) is not None:
                out += compare_trained(n, r, dat, placed(dat, uid(n)))
            elif f == "train.jsonl" and n in units:
                out += compare_trained(n, r, dat, units[n])
            elif n in techs:
                out += compare_tech(n, r, dat, techs[n])
    for kind, rate in tables.get("AOE2_WORK", {}).items():
        u = base_unit(dat, GATHERERS[kind]) if kind in GATHERERS else None
        got = work_rate(u) if u else None
        if got is not None and not same(rate, got):
            out.append(f"AOE2_WORK {kind}: {rate}, {round(got, 3)}")
    return out


def names():
    """{name: unit ID} and {name: tech ID} from the AoE2ScenarioParser enums (as units.type_ids, aoe2mc.object_kinds)."""
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.heroes import HeroInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    from AoE2ScenarioParser.datasets.techs import TechInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    units = {}
    for enum in (HeroInfo, UnitInfo, OtherInfo, BuildingInfo):     # later enums win, as in aoe2mc.object_kinds
        units |= {e.name: e.ID for e in enum}
    techs = {e.name: e.ID for e in TechInfo}
    techs |= {r["tech"]: techs[r["name"]] for r in rows("data/tech_names.jsonl") if r["name"] in techs}
    return units, techs


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else DEFAULT
    if not os.path.isfile(path):
        print(f"no .dat at {path}: give the path of empires2_x2_p1.dat (AoE2 DE, resources/_common/dat/)")
        return 2
    try:
        from genieutils.datfile import DatFile
    except ImportError:
        print("no genieutils-py: pip install genieutils-py")
        return 2
    sys.path.insert(0, ROOT)
    from game.gather import AOE2_WORK
    units, techs = names()
    tables = {f: rows(f"game/data/{f}") for f in ("units.jsonl", "buildings.jsonl", "train.jsonl", "build.jsonl",
                                                   "replay.jsonl")}
    tables["AOE2_WORK"] = AOE2_WORK
    lines = compare(DatFile.parse(path), units, techs, tables)
    print("\n".join(lines) or "no differences")
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main())
