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
# cTechState* of xs-check: the state of a technology for xsGetTechState
INVALID, DISABLED, NOT_READY, READY, RESEARCHING, DONE, QUEUED = -2, -1, 0, 1, 2, 3, 4
SET_ATTRIBUTE, MOD_RESOURCE, ENABLE_OBJECT, MUL_RESOURCE = 0, 1, 2, 6   # the effect IDs of xsEffectAmount


def civ_id(name):
    """The AoE2 civilization ID of a civilization key: its index in the enum of AoE2ScenarioParser (the .dat order,
    as tools/dat_compare.civ_ids), else 0."""
    from AoE2ScenarioParser.datasets.object_support import Civilization
    return next((i for i, c in enumerate(Civilization) if c.name == name), 0)


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

    def object_name(unit):
        n = aoe2mc.object_kinds().get(int(unit), (None, None))[1]
        if n is None:
            warn("object", unit)
        return n

    def available(unit, player):
        n, x = object_name(unit), side(player)
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
        elif int(e) == ENABLE_OBJECT and (n := object_name(o)):
            vars(x).setdefault("trigger_menus", {})[n] = bool(int(a))
        elif int(e) not in (MOD_RESOURCE, MUL_RESOURCE, ENABLE_OBJECT):
            warn("effect", e)

    return {"xsEffectAmount": effect,
            "xsGetGameTime": lambda: int(recap.game_time(g)),
            "xsGetObjectCount": count,
            "xsGetObjectCountTotal": lambda player, unit: count(player, unit, True),
            "xsGetPlayerCivilization": civilization,
            "xsGetPlayerNumberOfTechs": techs,
            "xsGetTechName": tech_name,
            "xsGetTechState": tech_state,
            "xsIsObjectAvailable": available,
            "xsPlayerAttribute": attribute,
            "xsResearchTechnology": research_tech,
            "xsSetPlayerAttribute": set_attribute,
            "xsSetTechName": set_tech_name,
            "xsSetTriggerVariable": set_variable,
            "xsTriggerVariable": variable}
