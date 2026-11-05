"""The game functions of an XS script (#5623, epic #5119): `host(g)` gives the `host` of `xs_run.Xs` for the side g (a
`gather.Gather`; the bots are `g.bots[i].g`, as in `scenario.attributes()`).

Minecraft feature: the scenario variables stay scores of `aoe_var` (the datapack triggers read them); the resources stay
in the stock of `Gather`. XS itself has no Minecraft feature (#5610). An unknown player or attribute gives one warning
line and 0, as an unknown name (`Xs.warn`), and the script goes on.
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mc  # noqa: E402
import units  # noqa: E402
from buildings import COLOR_NAMES  # noqa: E402

DIPLOMACY = (0, 1, 3)                                                  # DiplomacyState: ally, neutral, enemy

POPULATION = {11: (lambda x: x.units, lambda x: x.soldiers),           # cAttributePopulation
              37: (lambda x: x.units,),                                # cAttributeCivilianPopulation
              40: (lambda x: x.soldiers,)}                             # cAttributeMilitaryPopulation


def civ_id(name):
    """The AoE2 civilization ID of a civilization key: its index in the enum of AoE2ScenarioParser (the .dat order,
    as tools/dat_compare.civ_ids), else 0."""
    from AoE2ScenarioParser.datasets.object_support import Civilization
    return next((i for i, c in enumerate(Civilization) if c.name == name), 0)


def civ_name(civ):
    """The English name of a civilization key or ID ("BRITONS" or 1 -> "Britons"), else ""."""
    from AoE2ScenarioParser.datasets.object_support import Civilization
    names = [c.name for c in Civilization]
    key = names[civ] if isinstance(civ, int) and 0 <= civ < len(names) else civ if civ in names else ""
    return key.replace("_", " ").title()


def timer(g, hill=False):
    """(seconds left, player) of the victory timer that ends first: the wonders and the relics (as per.victory_data), or
    the King of the Hill monument (hill.py, on the Gather of player 1); (0, 0) with no timer."""
    import conquest  # conquest imports gather: import it late
    if hill:
        h = vars(conquest.main(g)).get("hill") or {}
        left = [(h["left"], h["owner"])] if h.get("owner") else []
    else:
        left = [(t["left"], t["player"]) for t in vars(g).get("wonders", {}).values()]
        left += [(t["left"], t["player"])] if (t := vars(g).get("relic_timer")) else []
    time, player = min(left, default=(0, 0))
    return max(math.ceil(time), 0), int(player)


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

    def color(n):
        return COLOR_NAMES[n - 1] if isinstance(n, int) and 1 <= n <= len(COLOR_NAMES) else None

    def row(player):
        return g.players.get(str(int(player))) if side(player) else None

    def stance(a, b):
        """The DiplomacyState of player a to player b (ALLY 0, NEUTRAL 1, ENEMY 3), as diplomacy.stance."""
        import gather
        if row(a) is None or row(b) is None:
            return -1
        return 0 if gather.allied(g.players, int(a), int(b)) else 1 if int(b) in row(a).get("neutral", ()) else 3

    def set_diplomacy(a, b, kind, mirror=False):
        """As "Change Diplomacy" (aoe2mc.diplomacy_lines): the score of aoe_dip, and scenario.diplomacy applies it."""
        a, b, kind = int(a), int(b), int(kind)
        if row(a) is None or row(b) is None or a == b or kind not in DIPLOMACY:
            return False
        for n, m in ((a, b), (b, a))[:1 + bool(mirror)]:
            g.command(f"scoreboard players set #p{n}.p{m} aoe_dip {kind + 1}")
        g.command("scoreboard players set #any aoe_dip 1")
        return True

    def declare_victory(player, victory=False):
        """As "Declare Victory" (aoe2mc.victory_lines): the score #p<N> of aoe_win, and scenario.victory ends the game.
        A defeat (victory false) has no form: one warning line."""
        if not victory:
            warn("defeat of player", player)
        elif side(player):
            g.command(f"scoreboard players set #p{int(player)} aoe_win 1")

    def set_name(player, key, name):
        if (r := row(player)) is None:
            return False
        r[key] = str(name)
        if key == "name":                                              # the team shows the name (Minecraft feature)
            g.command(f"team modify p{int(player)} displayName " + json.dumps(str(name)))
        return True

    def set_color(player, n):
        """As "Change Player Color" (aoe2mc.color_lines): the team color."""
        if (r := row(player)) is None or color(int(n)) is None:
            return False
        r["color"] = color(int(n))
        g.command(f"team modify p{int(player)} color {units.TEAM_COLOR[r['color']]}")
        return True

    def player_civ_name(player, localized=False):
        return (r.get("civ_name") or civ_name(r.get("civ", ""))) if (r := row(player)) else ""

    def color_tag(player):
        return f"<{r.get('color', '').upper()}>" if (r := row(player)) else ""

    def victory():
        from AoE2ScenarioParser.datasets.trigger_lists import SecondaryGameMode, VictoryCondition
        win = g.data.get("victory") or {}
        key = win.get("condition", "standard").upper().replace("-", "_")
        modes = sum(m.value for m in SecondaryGameMode if m.name.lower().replace("_", "-") in win.get("modes", ()))
        return (VictoryCondition[key].value if key in VictoryCondition.__members__ else 0), modes

    def victory_type():
        import per  # per imports gather: import it late
        return per.VICTORY_TYPES.get(getattr(g, "victory", "standard"), 0)

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

    return {"xsDeclareVictory": declare_victory,
            "xsGetCivName": lambda civ, localized=False: civ_name(int(civ)),
            "xsGetDamageClassName": enum_name("DamageClass"),
            "xsGetDiplomacy": stance,
            "xsGetGameTime": lambda: int(recap.game_time(g)),
            "xsGetObjectAttribute": object_attribute,
            "xsGetObjectAttributeName": enum_name("ObjectAttribute"),
            "xsGetObjectClass": object_class,
            "xsGetObjectCount": count,
            "xsGetObjectCountTotal": lambda player, unit: count(player, unit, True),
            "xsGetObjectName": object_name,
            "xsGetObjectType": object_type,
            "xsGetPlayerAttributeName": enum_name("Attribute"),
            "xsGetPlayerCivName": player_civ_name,
            "xsGetPlayerCivilization": civilization,
            "xsGetPlayerColorTag": color_tag,
            "xsGetPlayerNumberOfTechs": techs,
            "xsGetTaskAmount": lambda field=-1: task.get(int(field), 0.0),
            "xsGetVictoryCondition": lambda: victory()[0],
            "xsGetVictoryConditionForSecondaryGameMode": lambda: victory()[1],
            "xsGetVictoryPlayer": lambda: timer(g)[1],
            "xsGetVictoryPlayerForSecondaryGameMode": lambda: timer(g, True)[1],
            "xsGetVictoryTime": lambda: timer(g)[0],
            "xsGetVictoryTimeForSecondaryGameMode": lambda: timer(g, True)[0],
            "xsGetVictoryType": victory_type,
            "xsPlayerAttribute": attribute,
            "xsResetTaskAmount": task.clear,
            "xsSetDiplomacy": set_diplomacy,
            "xsSetPlayerAttribute": set_attribute,
            "xsSetPlayerCivName": lambda player, name="": set_name(player, "civ_name", name),
            "xsSetPlayerColor": set_color,
            "xsSetPlayerName": lambda player, name="": set_name(player, "name", name),
            "xsSetTriggerVariable": set_variable,
            "xsTaskAmount": task_amount,
            "xsTriggerVariable": variable}
