"""The game functions of an XS script (#5623, epic #5119): `host(g)` gives the `host` of `xs_run.Xs` for the side g (a
`gather.Gather`; the bots are `g.bots[i].g`, as in `scenario.attributes()`).

Minecraft feature: the scenario variables stay scores of `aoe_var` (the datapack triggers read them); the resources stay
in the stock of `Gather`. XS itself has no Minecraft feature (#5610). An unknown player or attribute gives one warning
line and 0, as an unknown name (`Xs.warn`), and the script goes on.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mc  # noqa: E402

POPULATION = {11: (lambda x: x.units, lambda x: x.soldiers),           # cAttributePopulation
              37: (lambda x: x.units,),                                # cAttributeCivilianPopulation
              40: (lambda x: x.soldiers,)}                             # cAttributeMilitaryPopulation


def civ_id(name):
    """The AoE2 civilization ID of a civilization key: its index in the enum of AoE2ScenarioParser (the .dat order,
    as tools/dat_compare.civ_ids), else 0."""
    from AoE2ScenarioParser.datasets.object_support import Civilization
    return next((i for i, c in enumerate(Civilization) if c.name == name), 0)


def host(g):
    """{XS name: callable} of the game functions for the side g."""
    import recap  # recap imports gather: import it late
    import train
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

    return {"xsGetDamageClassName": enum_name("DamageClass"),
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
            "xsGetPlayerNumberOfTechs": techs,
            "xsGetTaskAmount": lambda field=-1: task.get(int(field), 0.0),
            "xsPlayerAttribute": attribute,
            "xsResetTaskAmount": task.clear,
            "xsSetPlayerAttribute": set_attribute,
            "xsSetTriggerVariable": set_variable,
            "xsTaskAmount": task_amount,
            "xsTriggerVariable": variable}
