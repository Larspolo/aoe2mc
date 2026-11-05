"""The game functions of an XS script (#5623, epic #5119): `host(g)` gives the `host` of `xs_run.Xs` for the side g (a
`gather.Gather`; the bots are `g.bots[i].g`, as in `scenario.attributes()`).

Minecraft feature: the scenario variables stay scores of `aoe_var` (the datapack triggers read them); the resources stay
in the stock of `Gather`. XS itself has no Minecraft feature (#5610). An unknown player or attribute gives one warning
line and 0, as an unknown name (`Xs.warn`), and the script goes on.
The unit ids (#5837): a start object keeps the reference ID of the scenario ("ref" of aoe2mc.json), so the IDs of the
editor in a script name the same objects; a new object takes the next ID above all start IDs, and an ID is never given
again (the model of record.Recorder). The map key -> ID is on the main Gather (`xs_ids`, `xs_top`: one ID space for all
sides), and the saved game keeps it (savegame.OPTIONAL). The keys are those of per.standing: a unit UUID, the building
target UUID. The state of a unit comes from its entity (Health, Pos) or the score aoe_hp of a building, not a copy.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mc  # noqa: E402

POPULATION = {11: (lambda x: x.units, lambda x: x.soldiers),           # cAttributePopulation
              37: (lambda x: x.units,),                                # cAttributeCivilianPopulation
              40: (lambda x: x.soldiers,)}                             # cAttributeMilitaryPopulation
# cTechState* of xs-check: the state of a technology for xsGetTechState
INVALID, DISABLED, NOT_READY, READY, RESEARCHING, DONE, QUEUED = -2, -1, 0, 1, 2, 3, 4
SET_ATTRIBUTE, MOD_RESOURCE, ENABLE_OBJECT, MUL_RESOURCE = 0, 1, 2, 6   # the effect IDs of xsEffectAmount


def civ_id(name):
    """The AoE2 civilization ID of a civilization key: its index in the enum of AoE2ScenarioParser (the .dat order,
    as tools/dat_compare.civ_ids), else 0."""
    from AoE2ScenarioParser.datasets.object_support import Civilization
    return next((i for i, c in enumerate(Civilization) if c.name == name), 0)


def ids(g):
    """{key: XS id} of the objects of g, made at the first call (the start objects of aoe2mc.json, the module doc)."""
    import combat
    if "xs_ids" not in vars(g):
        objs = g.data.get("objects", [])
        keys = [(combat.target_uuid(o["footprint"]) if o["kind"] == "building" and "footprint" in o else o.get("uuid"),
                 o.get("ref")) for o in objs]
        g.xs_ids = {k: ref for k, ref in keys if k and ref is not None}
        g.xs_top = max((o.get("ref") or 0 for o in objs), default=0)
        for k, ref in keys:
            if k and ref is None and k not in g.xs_ids:
                g.xs_top += 1
                g.xs_ids[k] = g.xs_top
    return g.xs_ids


def objects(g):
    """[(XS id, Gather, key, game name)] of the standing objects of all sides; a new object gets the next id."""
    import per
    known, out = ids(g), []
    for x in [g, *(b.g for b in getattr(g, "bots", ()))]:
        names = {u["uuid"]: u["name"] for u in x.units if "uuid" in u}
        for key, name, _ in per.standing(x):
            if key not in known:
                g.xs_top += 1
                known[key] = g.xs_top
            out.append((known[key], x, key, names.get(key, name)))
    return out


def host(g):
    """{XS name: callable} of the game functions for the side g."""
    import recap  # recap imports gather: import it late
    import train

    import units
    warned = set()

    def warn(what, value):
        if (what, value) not in warned:
            warned.add((what, value))
            print(f"XS script: unknown {what} {value}: skipped", file=sys.stderr)

    def side(player):
        x = {s.player: s for s in [g, *(b.g for b in getattr(g, "bots", ()))]}.get(int(player))
        if x is None:
            warn("player", player)
        return x

    def resource(attribute):
        if 0 <= int(attribute) < len(aoe2mc.STORES):
            return aoe2mc.STORES[int(attribute)]
        warn("attribute", attribute)

    def attribute(player, a):
        if int(a) in POPULATION:                                       # the units of the side, not a stock (#5807)
            x = side(player)
            return float(sum(len(f(x)) for f in POPULATION[int(a)])) if x else 0.0
        x, r = side(player), resource(a)
        return float(x.stock.get(r, 0)) if x and r else 0.0

    def set_attribute(player, a, value):
        x, r = side(player), resource(a)
        if x and r:
            x.stock[r] = max(int(value), 0)
            x.show_stock()                                             # the board shows the stock (#3111)

    def names(x):
        return [*(o["name"] for o in x.units), *x.soldiers.values(), *train.owned(x)]

    def count(player, unit, total=False):
        if (x := side(player)) is None:
            return 0
        name = aoe2mc.object_kinds().get(int(unit), (None, None))[1]
        more = [s["name"] for s in x.sites if not s.get("done") and s["player"] == x.player] + \
            [e["name"] for q in x.queues.values() for e in q] if total else []
        return sum(n == name for n in names(x) + more)

    def variable(n):
        m = re.search(r" has (-?\d+) ", g.command(f"scoreboard players get #v{int(n)} aoe_var") or "")
        return int(m[1]) if m else 0

    def set_variable(n, value):
        g.command(f"scoreboard players set #v{int(n)} aoe_var {int(value)}")

    def civilization(player):
        import civs  # civs imports gather: import it late
        return civ_id(civs.real(g, player)) if side(player) else 0

    def techs(player):
        return len(x.techs) if (x := side(player)) else 0

    def tech(t):
        n = aoe2mc.tech_names().get(int(t))
        if n not in train.TECHS:
            warn("technology", t)
            return None
        return n

    def tech_state(t, player):
        import civs  # civs imports gather: import it late
        n, x = tech(t), side(player)
        if n is None or x is None:
            return INVALID
        if train.researched(x, n):
            return DONE
        if (q := next((q for q in x.queues.values() if any(e["name"] == n for e in q)), None)) is not None:
            return RESEARCHING if q[0]["name"] == n else QUEUED
        if civs.missing(x, n):
            return DISABLED
        return READY if train.unlocked(x, n) else NOT_READY

    def research_tech(t, force=False, available=False, player=-1):
        """As the trigger effect "Research Technology" (scenario.research): at no cost, now. Without force only a
        technology of the state READY (or NOT_READY with techAvailable)."""
        state = tech_state(t, player)
        if state in (INVALID, DONE) or not force and state not in (READY, *(NOT_READY,) * bool(available)):
            return False
        train.research(side(player), {"name": tech(t), "player": "@a"}, start=True)
        return True

    def tech_name(t, player=-1, internal=False):
        from AoE2ScenarioParser.datasets.techs import TechInfo
        if internal:
            return next((i.name for i in TechInfo if i.ID == int(t)), "")
        if (n := tech(t)) is None:
            return ""
        x = side(player) if int(player) > 0 else None
        return vars(x).get("trigger_names", {}).get(n) if x and n in vars(x).get("trigger_names", {}) else \
            train.ITEMS.get(n, (None, None, None))[2] or units.pretty(n)

    def set_tech_name(t, player, text):
        if (n := tech(t)) and (x := side(player)):                 # the menus show it (train.show, #2821)
            vars(x).setdefault("trigger_names", {})[n] = str(text)

    def object_key(unit):
        n = aoe2mc.object_kinds().get(int(unit), (None, None))[1]
        if n is None:
            warn("object", unit)
        return n

    def available(unit, player):
        n, x = object_key(unit), side(player)
        return bool(n and x and train.unlocked(x, n))

    def effect(e, o, a, value, player=-1, train_location=-1):
        """cModResource (a = cAttributeSet or cAttributeAdd), cMulResource and cEnableObject (as the trigger effect
        "Enable/Disable Object", g.trigger_menus). The unit attributes of the .dat have no table in the game program:
        one warning line."""
        x = side(player)
        if x is None:
            return
        if int(e) in (MOD_RESOURCE, MUL_RESOURCE) and (r := resource(o)):
            old = x.stock.get(r, 0)
            x.stock[r] = max(int(old * value if int(e) == MUL_RESOURCE else value + old * (int(a) == 1)), 0)
            x.show_stock()
        elif int(e) == ENABLE_OBJECT and (n := object_key(o)):
            vars(x).setdefault("trigger_menus", {})[n] = bool(int(a))
        elif int(e) not in (MOD_RESOURCE, MUL_RESOURCE, ENABLE_OBJECT):
            warn("effect", e)

    def unit(uid):
        """(Gather, key, game name) of the unit id, or None with one warning."""
        hit = next(((x, k, n) for i, x, k, n in objects(g) if i == int(uid)), None)
        if hit is None:
            warn("unit", uid)
        return hit

    def type_id(uid):
        import record
        return record.types().get(u[2], -1) if (u := unit(uid)) else -1

    def hitpoints(uid):
        if (u := unit(uid)) is None:
            return -1.0
        x, key, _ = u
        if key in getattr(x, "forts", ()):                             # a building: its score (bot.hp)
            m = re.search(r" has (-?\d+) ", x.command(f"scoreboard players get {key} aoe_hp") or "")
        else:
            import gather
            m = re.search(gather.NUMBER, (x.command(f"data get entity {key} Health") or "").rsplit(":", 1)[-1])
        return float(m[1]) if m else -1.0

    def position(uid):
        """The tiles (x, y) of the unit and 0: the units walk on the ground (per "point-z")."""
        if (u := unit(uid)) and (p := u[0].positions([u[1]]).get(u[1])) is not None:
            return (p[0] / u[0].map.T, p[2] / u[0].map.T, 0.0)
        return (-1.0, -1.0, -1.0)

    def held(uid, a):
        v = u[0].villagers.get(u[1]) if (u := unit(uid)) else None
        return float(v.load) if v and v.load and 0 <= int(a) < len(aoe2mc.STORES) and aoe2mc.STORES[int(a)] == v.res \
            else 0.0

    def civ_name(uid, localized=False):
        import civs
        return (civs.real(g, u[0].player) or "").replace("_", " ").title() if (u := unit(uid)) else ""

    def unit_name(uid, internal=False):
        if (u := unit(uid)) is None:
            return ""
        return u[2] if internal else u[2].replace("_", " ").capitalize()

    def unit_class(uid):
        import per
        return per.klass(u[2]) if (u := unit(uid)) else -1

    def kind(player, unit):
        """The side and the AoE2 name of object ID unit, or (None, None) with one warning line."""
        name = aoe2mc.object_kinds().get(int(unit), (None, None))[1]
        if name is None:
            warn("object", unit)
        return side(player), name

    def object_attribute(player=-1, unit=-1, a=-1, damage=-1):
        """A combat value of the unit type of the player (train.stats, with the trigger changes), as "Modify
        Variable by Attribute" (scenario.reads): the attributes of aoe2mc.STAT_ATTRIBUTES and CLASS_ATTRIBUTES."""
        import combat  # combat imports gather: import it late
        x, name = kind(player, unit)
        field = aoe2mc.STAT_ATTRIBUTES.get(int(a)) or aoe2mc.CLASS_ATTRIBUTES.get((int(a), int(damage)))
        if field is None:
            warn("object attribute", (a, damage))
        if not (x and name and field and name in combat.STATS):
            return 0.0
        return float(getattr(train.stats(x, name), field))

    def object_class(player=-1, unit=-1):
        """The first ObjectClass whose test of train.CLASSES holds for the unit type, else -1."""
        from AoE2ScenarioParser.datasets.trigger_lists import ObjectClass
        _, name = kind(player, unit)
        return next((c.value for c in ObjectClass if name and train.applies(f"@{c.name.lower()}", name)), -1)

    def object_type(player=-1, unit=-1):
        """The ObjectType: 2 building, 3 villager, 4 a unit with combat values, else 1 (other)."""
        import combat  # combat imports gather: import it late
        prefix, name = aoe2mc.object_kinds().get(int(unit), (None, None))
        if name is None:
            warn("object", unit)
            return -1
        return 2 if prefix == "B" else 3 if name.startswith("VILLAGER") else 4 if name in combat.STATS else 1

    def object_name(unit=-1, player=-1, internal=False):
        name = kind(player, unit)[1] if int(player) > 0 else aoe2mc.object_kinds().get(int(unit), (None, None))[1]
        return (name if internal else name.replace("_", " ").title()) if name else ""

    def enum_name(enum):
        """The name of an enum member of AoE2ScenarioParser by its ID: "" for an unknown ID."""
        def get(i=-1, localized=False):
            from AoE2ScenarioParser.datasets import trigger_lists
            e = getattr(trigger_lists, enum)
            n = e(int(i)).name if int(i) in set(e) else ""
            return n.replace("_", " ").title() if localized else n
        return get

    task = {}

    def task_amount(field=-1, value=-1.0):
        task[int(field)] = float(value)

    return {"xsDoesUnitExist": lambda uid: any(i == int(uid) for i, *_ in objects(g)),
            "xsEffectAmount": effect,
            "xsGetDamageClassName": enum_name("DamageClass"),
            "xsGetGameTime": lambda: int(recap.game_time(g)),
            "xsGetObjectAttribute": object_attribute,
            "xsGetObjectAttributeName": enum_name("ObjectAttribute"),
            "xsGetObjectClass": object_class,
            "xsGetObjectCount": count,
            "xsGetObjectCountTotal": lambda player, unit: count(player, unit, True),
            "xsGetObjectName": object_name,
            "xsGetObjectType": object_type,
            "xsGetPlayerAttributeName": enum_name("Attribute"),
            "xsGetPlayerCivilization": civilization,
            "xsGetPlayerNumberOfObjects": lambda player: sum(x is side(player) for _, x, _, _ in objects(g)),
            "xsGetPlayerNumberOfTechs": techs,
            "xsGetTaskAmount": lambda field=-1: task.get(int(field), 0.0),
            "xsGetTechName": tech_name,
            "xsGetTechState": tech_state,
            "xsGetUnitAttributeHeld": held,
            "xsGetUnitCivName": civ_name,
            "xsGetUnitClass": unit_class,
            "xsGetUnitCopyId": type_id,
            "xsGetUnitHitpoints": hitpoints,
            "xsGetUnitName": unit_name,
            "xsGetUnitObjectId": type_id,
            "xsGetUnitOwner": lambda uid: u[0].player if (u := unit(uid)) else -1,
            "xsGetUnitPosition": position,
            "xsIsObjectAvailable": available,
            "xsIsObjectValid": lambda oid, player=-1: int(oid) in aoe2mc.object_kinds(),
            "xsPlayerAttribute": attribute,
            "xsResearchTechnology": research_tech,
            "xsResetTaskAmount": task.clear,
            "xsSetPlayerAttribute": set_attribute,
            "xsSetTechName": set_tech_name,
            "xsSetTriggerVariable": set_variable,
            "xsTaskAmount": task_amount,
            "xsTriggerVariable": variable}
