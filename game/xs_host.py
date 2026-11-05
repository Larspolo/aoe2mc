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

    ctx = [None]                                                       # xsSetContextPlayer; None: the first AI script

    def script():
        """The AI script (per.Script) of the context player: the XS functions of the AI act on it (#5846)."""
        bots = [b for b in getattr(g, "bots", ()) if getattr(b, "script", None)]
        b = next((b for b in bots if ctx[0] is None or b.g.player == ctx[0]), None)
        if b is None:
            warn("AI script of player", ctx[0])
        return b and b.script

    def get(what, n, default=0):
        if (s := script()) is None:
            return default
        if what == "goal":
            return int(s.goals.get(int(n), 0 if 1 <= int(n) <= 512 else -1))
        if what == "sn":
            import per
            if (name := per.SN_IDS.get(int(n))) is None:
                return warn("strategic number", n) or default
            return int(s.number(name))
        return s.table(what).get(int(n), 0)                            # "signal"; "event": the AI script goal

    def put(what, n, value):
        if (s := script()) is None:
            return
        if what == "goal":
            s.goals[int(n)] = int(value)
        elif what == "sn":
            import per
            if (name := per.SN_IDS.get(int(n))) is None:
                return warn("strategic number", n)
            s.sn[name] = int(value)
        else:
            s.table(what)[int(n)] = int(value)

    def set_context(player):
        ctx[0] = int(player)

    return {"xsGetAiScriptGoal": lambda n=-1: bool(get("event", n)),
            "xsGetAiSignal": lambda n=-1, legacy=False: get("signal", n),
            "xsGetContextPlayer": lambda: -1 if ctx[0] is None else ctx[0],
            "xsGetGameTime": lambda: int(recap.game_time(g)),
            "xsGetGoal": lambda n=-1: get("goal", n, -1),
            "xsGetObjectCount": count,
            "xsGetObjectCountTotal": lambda player, unit: count(player, unit, True),
            "xsGetPlayerCivilization": civilization,
            "xsGetPlayerNumberOfTechs": techs,
            "xsGetStrategicNumber": lambda n=-1: get("sn", n, -1),
            "xsPlayerAttribute": attribute,
            "xsSetAiScriptGoal": lambda n=-1, v=False: put("event", n, bool(v)) or True,
            "xsSetAiSignal": lambda n=-1, v=-1, legacy=False: put("signal", n, v),
            "xsSetContextPlayer": set_context,
            "xsSetGoal": lambda n=-1, v=-1: put("goal", n, v),
            "xsSetPlayerAttribute": set_attribute,
            "xsSetStrategicNumber": lambda n=-1, v=-1: put("sn", n, v),
            "xsSetTriggerVariable": set_variable,
            "xsTriggerVariable": variable}
