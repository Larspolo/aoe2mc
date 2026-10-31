#!/usr/bin/env python3
"""Compare the AoE2 values of the data files with the .dat of an installed AoE2 DE game (#5245).

Usage: python3 tools/dat_compare.py [PATH/empires2_x2_p1.dat] [--write DIR [--base BASE.dat]]

Prints one line for each difference ("NAME key: data value, game value"). Exit 0: no difference, 1: differences,
2: no .dat or no genieutils-py. With --write DIR, PATH is the .dat of a data mod: the tool writes the unit values of
the mod that differ from the base game (BASE.dat, default the installed game) as data mod lines (DIR/units.jsonl ...,
epic #5352, #5354) and prints their count. The rules of the compare: tickets #5245 and #5297 (epic #5236). When the .dat and
the AoE2 wiki do not agree, the .dat wins (docs/research/gameplay.md).
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
           26: "castle", 27: "spearman", 28: "cavalry_archer", 29: "eagle", 30: "camel", 32: "condottiero", 35: "mameluke",
           37: "heavysiege", 38: "skirmisher", 41: "fireship", 60: "warship"}
IGNORE_CLASS = 31
VILLAGER = 118                                  # rule 5: the train location of a placed building
RESOURCES = {0: "food", 1: "wood", 2: "stone", 3: "gold"}
# The villager unit of each gather kind of gather.AOE2_WORK (the oyster: no own unit).
GATHERERS = {"farm": 214, "fish": 56, "food": 120, "gold": 579, "hunt": 122, "stone": 124, "wood": 123}
# Lines that keep the values of another unit of the .dat on purpose (#5297), one entry per line.
SAME_AS = {
    "CAMEL": 329,           # replay.jsonl: the Camel Rider, not the camel animal 897
    "POLEMARCH": 2164,      # the Civic Age values ("Polemarch 2")
    "TREBUCHET": 331,       # the packed values; game/trebuchet.py sets the unpacked armor (#1409)
}
# Differences that aoe2mc keeps on purpose (#5297): (name, key): the reason, one entry per line.
ACCEPTED = {
    ("AOE2_WORK", "farm"): "an aoe2mc farmer stands still: 0.33 is the farm rate that an AoE2 player gets (#5244)",
    ("ECONOMIC_POLICY", "cost"): "the Athenian policies are switches: aoe2mc takes the cost from civs.jsonl (policies)",
    ("ECONOMIC_POLICY", "time"): "the Athenian policies are switches: the game gives time 0, aoe2mc keeps its own switch time (#5305)",
    ("MILITARY_POLICY", "cost"): "the Athenian policies are switches: aoe2mc takes the cost from civs.jsonl (policies)",
    ("NAVAL_POLICY", "cost"): "the Athenian policies are switches: aoe2mc takes the cost from civs.jsonl (policies)",
}


def rows(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def most_common(values):
    """Rule 1: the base value is the most common value over all civilizations."""
    values = [v for v in values if v is not None]
    return Counter(values).most_common(1)[0][0] if values else None


def base_unit(dat, uid):
    """The unit of the most common civilization variant (rule 1): the unit of the first civilization (no Gaia) whose
    hit points, attack and armor are the most common ones. A unit of Gaia only (the wild animals): the Gaia unit."""
    units = [c.units[uid] for c in dat.civs[1:] if uid < len(c.units) and c.units[uid] is not None]
    units = units or [c.units[uid] for c in dat.civs[:1] if uid < len(c.units) and c.units[uid] is not None]
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
    d = {"hp": u.hit_points, "sight": round(u.line_of_sight, 2)}
    if t:                           # the range in tiles: 2.5 for the fire ships (#5297); no negative bonus (epic #5236)
        d |= {"attack": max(atk.get(4, 0), atk.get(3, 0)), "melee": arm.get(4, 0), "pierce": arm.get(3, 0),
              "range": round(t.max_range, 2), "reload": round(t.reload_time, 3),
              "bonus": {CLASSES[c]: a for c, a in sorted(atk.items()) if c in CLASSES and c not in (3, 4) and a > 0}}
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


def variants(dat, u, civs=()):
    """Unit u in each age (rule 2) and with each technology of the civilizations civs (rule 7: the IDs of the
    civilizations of the line; the technologies of the other civilizations explain no value, #5297)."""
    out, cur = [u], copy.deepcopy(u)
    for age in AGES:
        for e in age:
            if e < len(dat.effects):
                apply(cur, dat.effects[e])
        out.append(copy.deepcopy(cur))
    for t in dat.techs:
        if getattr(t, "civ", 0) in civs and 0 <= t.effect_id < len(dat.effects):
            v = copy.deepcopy(u)
            apply(v, dat.effects[t.effect_id])
            out.append(v)
    return out


def same(a, b, tolerance=0.011):
    """Two values agree: numbers within the tolerance (the float of 2.15 against 2.16 of the data, #5297)."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tolerance
    return a == b


def by_villager(u):
    return bool(u.creatable) and any(loc.unit_id == VILLAGER for loc in u.creatable.train_locations)


def finished(dat, uid):
    """Rule 5: a building that villagers place has the values of its finished unit (`building.stack_unit_id`: the
    gate segments 64, 63 and 789 of the placed gates 487, 488 and 792, #5297)."""
    u = base_unit(dat, uid)
    stack = getattr(getattr(u, "building", None), "stack_unit_id", -1)
    return stack if u is not None and by_villager(u) and stack >= 0 and base_unit(dat, stack) else uid


def compare_unit(name, data, dat, uid):
    """The difference lines of one row of units.jsonl or buildings.jsonl (keys of the row only)."""
    u = base_unit(dat, finished(dat, uid))
    if u is None:
        return [f"{name}: no unit {uid} in the .dat"]
    found = [stats(v) for v in variants(dat, u)]
    out = []
    for k in ("hp", "attack", "melee", "pierce", "range", "reload", "sight", "walk"):
        if k == "reload" and not (data.get(k) and found[0].get(k)):
            continue                     # no attack cycle: monks, Petard, Saboteur, Flaming Camel (#5297)
        if k in data and k in found[0] and not any(same(data[k], f.get(k)) for f in found):
            out.append(f"{name} {k}: {data[k]}, {found[0][k]}")
    if "bonus" in data and "bonus" in found[0]:
        bonus = {c: a for c, a in data["bonus"].items() if a > 0}        # no negative bonus (epic #5236)
        if not any(bonus == f.get("bonus") for f in found):
            out.append(f"{name} bonus: {bonus}, {found[0]['bonus']}")
    return out


def cost(costs):
    """Rule 6: a cost with flag 0 is not paid."""
    return {RESOURCES[c.type]: c.amount for c in costs if c.flag and c.amount and c.type in RESOURCES}


def compare_cost(name, data, game_cost, game_time, times=()):
    out = []
    if "cost" in data and data["cost"] != game_cost:
        out.append(f"{name} cost: {data['cost']}, {game_cost}")
    times = [t for t in (game_time, *times) if t is not None]      # whole seconds: 125 × 0.667 is 83 (#5297)
    if "time" in data and game_time is not None and not any(same(data["time"], t, 0.5) for t in times):
        out.append(f"{name} time: {data['time']}, {game_time}")
    return out


def train_time(u):
    locs = u.creatable.train_locations if u.creatable else []
    return locs[0].train_time if locs else None


def compare_trained(name, data, dat, uid, civs=()):
    u = base_unit(dat, uid)
    if u is None or not u.creatable:
        return [f"{name}: no unit {uid} in the .dat"]
    return compare_cost(name, data, cost(u.creatable.resource_costs), train_time(u),
                        [train_time(v) for v in variants(dat, u, civs)])


def compare_tech(name, data, dat, tid):
    if tid >= len(dat.techs):
        return [f"{name}: no technology {tid} in the .dat"]
    t = dat.techs[tid]
    locs = getattr(t, "research_locations", None) or []
    return compare_cost(name, data, cost(t.resource_costs), locs[0].research_time if locs else None)


def placed(dat, uid):
    """Rule 5: the building unit that villagers place (train location 118): uid, else the head unit of the finished
    building (`building.head_unit`: Town Center 109 → 621, Pasture 1897 → 1889, #5297), else the unit of the same
    name."""
    u = base_unit(dat, uid)
    if u is None or by_villager(u):
        return uid
    head = getattr(getattr(u, "building", None), "head_unit", -1)
    v = base_unit(dat, head) if head >= 0 else None
    if v is not None and by_villager(v):
        return head
    for c in dat.civs[1:2]:
        for v in c.units:
            if v is not None and v.name == u.name and by_villager(v):
                return v.id
    return uid


def work_rate(u):
    """The work rate of a villager unit (`bird.work_rate`; the work value of its gather task is 1.0, #5297)."""
    return u.bird.work_rate if u.bird else None


def line_civs(row, civs):
    """Rule 7: the .dat indexes of the civilizations of a line of train.jsonl or build.jsonl (`civ`, `civs`)."""
    keys = [row["civ"]] if isinstance(row.get("civ"), str) else row.get("civs") or []
    return tuple(civs[k] for k in keys if k in (civs or {}))


def compare(dat, units, techs, tables, civs=None):
    """All difference lines. units: {name: unit ID}, techs: {name: tech ID}; tables: {file: rows}, with the gather
    rates as the rows of "AOE2_WORK"; civs: {civilization key: .dat index} (rule 7)."""
    out = []
    uid = lambda n: SAME_AS.get(n, units.get(n))
    for f in ("units.jsonl", "buildings.jsonl", "replay.jsonl"):
        for r in tables.get(f, ()):
            i = uid(r["name"])
            if i is not None:
                out += compare_unit(r["name"], {"walk": r["walk"]} if "walk" in r else r, dat, i)
    for f in ("train.jsonl", "build.jsonl"):
        for r in tables.get(f, ()):
            n, own = r["name"], line_civs(r, civs)
            if f == "build.jsonl" and uid(n) is not None:
                out += compare_trained(n, r, dat, placed(dat, uid(n)), own)
            elif f == "train.jsonl" and ("effect" in r or r.get("item") == "book"):
                if n in techs:                                  # a technology line, also with a unit name (#5297)
                    out += compare_tech(n, r, dat, techs[n])
            elif f == "train.jsonl":
                if uid(n) is not None:                          # a unit line: never the technology of its name
                    out += compare_trained(n, r, dat, uid(n), own)
            elif n in techs:
                out += compare_tech(n, r, dat, techs[n])
    for kind, rate in tables.get("AOE2_WORK", {}).items():
        u = base_unit(dat, GATHERERS[kind]) if kind in GATHERERS else None
        got = work_rate(u) if u else None
        if got is not None and not same(rate, got):
            out.append(f"AOE2_WORK {kind}: {rate}, {round(got, 3)}")
    return [x for x in out if not accepted(x)]


def accepted(line):
    """True when the name and the key of a line ("NAME key: ...") are in ACCEPTED (#5305)."""
    head = line.split(":")[0].split()
    return len(head) == 2 and tuple(head) in ACCEPTED


def unit_values(dat, uid):
    """stats() of unit uid in each age (rule 2, the variants of compare_unit), or None."""
    u = base_unit(dat, finished(dat, uid))
    return None if u is None else [stats(v) for v in variants(dat, u)]


def mod_values(name, data, base, mod, uid):
    """The keys of one row of units.jsonl, buildings.jsonl or replay.jsonl whose value the mod .dat changes (#5354).
    The value is that of the age at which the base .dat has the data value (rule 2: aoe2mc keeps the value of the
    first age of a unit, the Donjon in the Feudal Age): the mod value of the same age, also when the mod changes
    the age effects. A key that the base .dat does not explain (ACCEPTED, own values) keeps the data value."""
    old, new = unit_values(base, uid), unit_values(mod, uid)
    out = {}
    for k in ("hp", "attack", "melee", "pierce", "range", "reload", "sight", "walk", "bonus"):
        if not old or not new or k not in data or k not in old[0] or k not in new[0] or (name, k) in ACCEPTED:
            continue
        if k == "reload" and not (data[k] and old[0][k]):
            continue                     # no attack cycle (compare_unit)
        want = {c: a for c, a in data[k].items() if a > 0} if k == "bonus" else data[k]   # no negative bonus
        age = next((i for i, f in enumerate(old) if same(want, f.get(k))), None)
        if age is None or same(want, new[age].get(k)):
            continue
        out[k] = {**{c: a for c, a in data[k].items() if a <= 0}, **new[age][k]} if k == "bonus" else new[age][k]
    return out


def write(base, mod, units, tables, folder):
    """Write the data mod lines of the mod .dat into folder (#5354): one file for each unit file of tables (also
    with no line, so an older line goes), one line per changed name with only its changed keys. Returns the count."""
    os.makedirs(folder, exist_ok=True)
    count = 0
    for f in ("units.jsonl", "buildings.jsonl", "replay.jsonl"):
        lines = []
        for r in tables.get(f, ()):
            i = SAME_AS.get(r["name"], units.get(r["name"]))
            d = {} if i is None else mod_values(r["name"], {"walk": r["walk"]} if "walk" in r else r, base, mod, i)
            if d:
                lines.append(json.dumps({"name": r["name"], **d}, ensure_ascii=False))
        with open(os.path.join(folder, f), "w", encoding="utf-8") as out:
            out.write("".join(s + "\n" for s in lines))
        count += len(lines)
    return count


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
    techs |= {r["name"]: techs[r["tech"]] for r in rows("data/tech_names.jsonl") if r["tech"] in techs}   # #5297
    return units, techs


def civ_ids():
    """Rule 7: {civilization key: .dat index}; the order of the AoE2ScenarioParser enum is the order of the .dat."""
    from AoE2ScenarioParser.datasets.object_support import Civilization
    return {c.name: i for i, c in enumerate(Civilization)}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    opt = {}
    for key in ("--write", "--base"):
        if key in argv[:-1]:
            i = argv.index(key)
            opt[key] = argv.pop(i + 1)
            argv.pop(i)
    path = argv[0] if argv else DEFAULT
    base = opt.get("--base", DEFAULT)
    for p in (path, base) if "--write" in opt else (path,):
        if not os.path.isfile(p):
            print(f"no .dat at {p}: give the path of empires2_x2_p1.dat (AoE2 DE, resources/_common/dat/)")
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
    if "--write" in opt:
        n = write(DatFile.parse(base), DatFile.parse(path), units, tables, opt["--write"])
        print(f"{n} data mod lines in {opt['--write']}")
        return 0
    lines = compare(DatFile.parse(path), units, techs, tables, civ_ids())
    print("\n".join(lines) or "no differences")
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main())
